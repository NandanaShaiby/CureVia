from selectors import SelectSelector

from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
import uuid
from django.utils import timezone
from collections import defaultdict
from .models import *
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.cache import never_cache
import random

def index(request):
    return render(request, "index.html")

def reg(request):
    msg = False
    if request.method == "POST":
        f = request.POST.get("fname")
        l = request.POST.get("lname")
        e = request.POST.get("email")
        ph = request.POST.get("phone")
        g = request.POST.get("gender")
        dob = request.POST.get("dob")
        p = request.POST.get("password")
        reg = Register(fname=f, lname=l, email=e, phone=ph, password=p, gender=g, dob=dob)
        reg.save()
        msg = True
    return render(request, "register.html", {"msg": msg})

def login(request):
    msg = False
    if request.method == "POST":
        e = request.POST.get("email")
        p = request.POST.get("password")
        remember_me = request.POST.get("remember_me")
        log = Register.objects.filter(email=e, password=p)
        plog=Pharmacy.objects.filter(email=e, password=p)
        dlog=DeliveryAgent.objects.filter(email=e, password=p)
        if log or plog or dlog:
            if remember_me:
                request.session.set_expiry(1209600)  # 2 weeks (in seconds)
            else:
                request.session.set_expiry(0)  # Expires when browser closes
        if log:
            for i in log:
                request.session['user_id'] = i.id
                r = i.rights
                if r == "user":
                    request.session['uid'] = i.id
                    return redirect("/user")
                elif r == "admin":
                    return redirect("/adminp")
        elif plog:
            for i in plog:
                request.session['pharmacy_id'] = i.id
                return redirect("/pharmacy_staff_login")
        elif dlog:
            for i in dlog:
                request.session['did'] = i.id
                return redirect("/delivery_home")

        else:
            msg = True
    return render(request, "login.html",{"msg":msg})

@never_cache
def user(request):
    if 'user_id' in request.session:
        uid = request.session['user_id']
        current_user = get_object_or_404(Register, id=uid)
        current_pincode = request.session.get('user_pincode')
        if not current_pincode and current_user.zip:
            current_pincode = current_user.zip
            request.session['user_pincode'] = current_pincode
        popular_products = Medicine.objects.filter(is_popular=True)
        new_products = Medicine.objects.all().order_by('-id')[:6]
        return render(request, "user/userhome.html", {'user': current_user, 'products': popular_products,'new_products': new_products, 'current_pincode': current_pincode or "Select Location"})
    else:
        return redirect("/login")

@never_cache
def admin(request):
    if 'user_id' in request.session:
        # Verify it's actually an admin (Optional but recommended)
        uid = request.session['user_id']
        try:
            user_obj = Register.objects.get(id=uid)
            if user_obj.rights != 'admin':
                return redirect('/login/')
        except Register.DoesNotExist:
            return redirect('/login/')

        # 1. Calculate Stats
        total_orders = Order.objects.count()
        total_customers = Register.objects.exclude(rights='admin').count()

        # Calculate Revenue
        all_orders = Order.objects.select_related('medicine')
        total_revenue = sum(item.quantity * item.medicine.price for item in all_orders)

        # 2. Get Recent Orders
        recent_orders = Order.objects.select_related(
            'user', 'medicine'
        ).order_by('-created_at')[:10]

        # 3. Context Dictionary
        context = {
            'total_orders': total_orders,
            'total_customers': total_customers,
            'total_revenue': total_revenue,
            'recent_orders': recent_orders
        }

        return render(request, "admin/adminhome.html", context)

    else:
        return redirect('/login/')

@never_cache
def pharmacist(request):
    # CHANGED: Check for 'pharmacy_id' instead of 'pid'
    if 'pharmacy_id' in request.session:
        pid = request.session['pharmacy_id']
        staff_name = request.session.get('staff_name', 'Staff')

        # CHANGED: Get the Pharmacy Object directly
        my_pharmacy = get_object_or_404(Pharmacy, id=pid)

        # 1. Pending Prescriptions
        pending_prescriptions = Prescription.objects.filter(
            assigned_pharmacy=my_pharmacy,
            status__in=['Assigned to Pharmacy', 'Under Review']
        ).order_by('-created_at')

        # 2. Pending Orders
        pending_orders = Order.objects.filter(
            assigned_pharmacy=my_pharmacy,
            status__in=['Pending', 'Packed', 'Confirmed','Out for Pickup']
        ).order_by('order_group_id', '-created_at')

        # 3. Low Stock (Linked directly to pharmacy now)
        low_stock_meds = Medicine.objects.filter(
            added_by_pharmacy=my_pharmacy,
            quantity__lt=10
        )

        context = {
            'pharmacy': my_pharmacy,
            'staff_name': staff_name,  # Pass name for display
            'pending_prescriptions': pending_prescriptions,
            'pending_orders': pending_orders,
            'low_stock_meds': low_stock_meds,
        }
        return render(request, "pharmacist/pharhome.html", context)
    else:
        return redirect('/login/')

@never_cache
def customer(request):
    us=Register.objects.exclude(rights='admin')
    return render(request, "admin/customer.html",{"us":us})

def blockuser(request,id):
    Register.objects.filter(id=id).update(rights='Blocked')
    return redirect("/customer/")

def unblock(request,id):
    Register.objects.filter(id=id).update(rights='user')
    return redirect("/customer/")

@never_cache
def edituser(request,id):
    customer = get_object_or_404(Register, id=id)

    if request.method == 'POST':

        new_fname = request.POST.get('fname')
        new_lname = request.POST.get('lname')
        new_email = request.POST.get('email')
        new_phone = request.POST.get('phone')

        customer.fname = new_fname
        customer.lname = new_lname
        customer.email = new_email
        customer.phone = new_phone

        customer.save()

        return redirect("/customer/")

    else:

        context = {
            'customer': customer
        }
        return render(request, 'admin/edit_user.html', context)

@never_cache
def adduser(request):
    if request.method == 'POST':
        f = request.POST.get('fname')
        l = request.POST.get('lname')
        e = request.POST.get('email')
        ph = request.POST.get('phone')
        g = request.POST.get("gender")
        dob = request.POST.get("dob")
        p = request.POST.get("password")

        customer = Register(
            fname=f,
            lname=l,
            email=e,
            phone=ph,
            password=p,
            gender=g,
            dob=dob
        )
        customer.save()
        return redirect("/customer/")

    return render(request, 'admin/add_user.html')

@login_required
def addmed(request):
    # 1. FIX: Check for the correct session key
    if 'pharmacy_id' not in request.session:
        return redirect('/login/')

    pid = request.session['pharmacy_id']
    ph = get_object_or_404(Pharmacy, id=pid)
    addmed = Category.objects.all()

    if request.method == 'POST':
        n = request.POST.get('name')
        c = request.POST.get('category')
        p = request.POST.get('purpose')
        d = request.POST.get('description')
        pr = request.POST.get("price")
        q = request.POST.get("quantity")
        rx = 'rx_required' in request.POST
        ex = request.POST.get("expiry")
        i = request.FILES.get("image")

        c_obj = Category.objects.get(id=c)
        Medicine.objects.create(
            name=n,
            category=c_obj,
            purpose=p,
            description=d,
            price=pr,
            quantity=q,
            rx_required=rx,
            expiry_date=ex,
            image=i,
            # 2. FIX: Link to Pharmacy, not Pharmacist
            added_by_pharmacy=ph
        )

        return redirect("/addmed/")

    return render(request, 'pharmacist/add_medicine.html', {'addmed': addmed})

def shop(request):
    products = Medicine.objects.all().order_by('-id')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        products = products.filter(price__gte=min_price, price__lte=max_price)
    sort_by = request.GET.get('sort', 'relevance')  # Default to 'relevance'

    if sort_by == 'name_asc':
            products = products.order_by('name')  # A to Z
    elif sort_by == 'name_desc':
            products = products.order_by('-name')  # Z to A
    elif sort_by == 'price_asc':
            products = products.order_by('price')  # Low to High
    elif sort_by == 'price_desc':
            products = products.order_by('-price')  # High to Low
    else:
            products = products.order_by('-id')  # Relevance (Newest)

    current_user = None
    if 'uid' in request.session:
        current_user = Register.objects.filter(id=request.session['uid']).first()

    context = {
        'products': products,
        'min_price': min_price,
        'max_price': max_price,
        'current_sort': sort_by,
    }
    return render(request, "user/shop.html",context)

def about(request):
    return render(request, "user/about.html")

def contact(request):
    return render(request, "user/contact.html")

def userprofile(request,id):
    user = get_object_or_404(Register, id=id)

    if request.method == 'POST':

        new_fname = request.POST.get('fname')
        new_lname = request.POST.get('lname')
        new_email = request.POST.get('email')
        new_phone = request.POST.get('phone')
        new_gender = request.POST.get('gender')
        new_dob = request.POST.get('dob')


        user.fname = new_fname
        user.lname = new_lname
        user.email = new_email
        user.phone = new_phone
        user.gender = new_gender
        user.dob = new_dob
        old_pass = request.POST.get('old_password')
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')
        if old_pass and new_pass and confirm_pass:
            if user.password == old_pass:
                if new_pass == confirm_pass:
                    user.password = new_pass
                    #messages.success(request, "Profile and password updated successfully!")
                else:
                   # messages.error(request, "New password and confirm password do not match.")
                   return redirect(f"/userprofile/{id}/")
            else:
               # messages.error(request, "Incorrect old password.")
               return redirect(f"/userprofile/{id}/")

        user.save()

        return redirect(f"/userprofile/{id}/")

    else:

        context = {
            'user': user
        }
        return render(request, 'user/userprofile.html', context)


def single_product(request, id):
    product = get_object_or_404(Medicine, id=id)

    # Default status is None (Assume no prescription uploaded yet)
    p_status = None

    # Logic: If user is logged in, check if they uploaded a prescription
    if 'uid' in request.session:
        uid = request.session['uid']
        user = Register.objects.get(id=uid)

        # Check the database for the LATEST upload for this specific medicine
        # We use .last() to get the most recent attempt
        pres = Prescription.objects.filter(user=user, medicine=product).last()

        if pres:
            p_status = pres.status

    context = {
        'product': product,
        'p_status': p_status  # <--- THIS IS CRITICAL. The HTML needs this!
    }
    return render(request, "user/shop-single.html", context)

def cart(request):
    uid=request.session['uid']
    reg=Register.objects.get(id=uid)
    c=Cart.objects.filter(user=reg)

    return render(request, "user/cart.html", {'cart':c})


def addcart(request, id):
    uid = request.session['uid']
    reg = Register.objects.get(id=uid)
    med = Medicine.objects.get(id=id)

    # --- SECURITY CHECK ---
    if med.rx_required:
        # Check if there is ANY prescription with status 'Approved' for this user/med
        # .exists() returns True or False
        is_approved = Prescription.objects.filter(user=reg, medicine=med, status='Approved').exists()

        if not is_approved:
            # If not approved, kick them back to the product page
            return redirect(f'/shop/{id}/')
    # ----------------------

    # Add to cart (Your original logic)
    c = Cart(user=reg, medicine=med, quantity=1)
    c.save()
    return redirect('/cart/')

def deletecart(request,id):
    Cart.objects.filter(id=id).delete()
    return redirect('/cart/')

def checkout(request):
    uid=request.session['uid']
    reg=Register.objects.get(id=uid)
    cart=Cart.objects.filter(user=reg)
    total_price=0
    for i in cart:
        total=i.total_price
        total_price+=total
    if request.method == "POST":
        f = request.POST.get("fname")
        l = request.POST.get("lname")
        e = request.POST.get("email")
        ph = request.POST.get("phone")
        c = request.POST.get("country")
        st = request.POST.get("state")
        z= request.POST.get("zip")
        a=request.POST.get("address")
        n=request.POST.get("notes")

        request.session['fname']=f
        request.session['lname']=l
        request.session['email']=e
        request.session['phone']=ph
        request.session['country']=c
        request.session['state']=st
        request.session['zip']=z
        request.session['address']=a
        request.session['notes']=n

        return redirect('/payment/')

    return render(request, "user/checkout.html",{'cart':cart,'total_price':total_price})

def payment(request):


    return render(request, "user/payment.html")

def confirmpayment(request):
    uid = request.session['uid']
    reg = Register.objects.get(id=uid)
    cart = Cart.objects.filter(user=reg)
    f=request.session['fname']
    l=request.session['lname']
    e=request.session['email']
    ph=request.session['phone']
    c=request.session['country']
    st=request.session['state']
    z=request.session['zip']
    a=request.session['address']
    n=request.session['notes']

    for i in cart:
        ch = Order(medicine=i.medicine, user=reg, quantity=i.quantity, fname=f, lname=l, email=e, phone=ph, country=c,
                   state=st, zip=z, address=a, notes=n)
        ch.save()
        cart.delete()
    return redirect('/thanku/')


def thanku(request):
    return render(request, "user/thankyou.html")

def search_product(request):
    query = request.GET.get('q')
    pincode = request.GET.get('pincode')

    # Session Management
    if pincode:
        request.session['user_pincode'] = pincode
    else:
        pincode = request.session.get('user_pincode')

    products_list = []
    locked_pharmacy = None  # Flag to tell HTML if we are restricted

    # --- 1. CHECK CART STATUS ---
    if 'uid' in request.session:
        user = Register.objects.get(id=request.session['uid'])
        existing_cart_item = Cart.objects.filter(user=user).first()

        if existing_cart_item:
            # CART IS NOT EMPTY -> LOCK THE SEARCH
            locked_pharmacy = existing_cart_item.medicine.added_by_pharmacy

    if query:
        # --- SCENARIO A: CART LOCKED (Search only specific pharmacy) ---
        if locked_pharmacy:
            # We skip the deduplication logic because we are only looking at ONE store.
            products_list = Medicine.objects.filter(
                Q(name__icontains=query) |
                Q(purpose__icontains=query) |
                Q(category__name__icontains=query),

                # STRICT FILTER: Only this pharmacy
                added_by_pharmacy=locked_pharmacy
            )

        # --- SCENARIO B: GLOBAL SEARCH (Best Price Logic) ---
        else:
            all_matches = Medicine.objects.filter(
                Q(name__icontains=query) |
                Q(purpose__icontains=query) |
                Q(category__name__icontains=query)
            )

            # Filter by Pincode
            if pincode:
                all_matches = all_matches.filter(
                    added_by_pharmacy__service_pincodes__icontains=pincode,
                    added_by_pharmacy__is_active=True
                )

            # Deduplicate (Show Best Price)
            unique_medicines = {}
            for med in all_matches:
                name_key = med.name.strip().lower()
                if name_key in unique_medicines:
                    if med.price < unique_medicines[name_key].price:
                        unique_medicines[name_key] = med
                else:
                    unique_medicines[name_key] = med

            products_list = list(unique_medicines.values())

    context = {
        'products': products_list,
        'query': query,
        'pincode': pincode,
        'locked_pharmacy': locked_pharmacy  # Pass this to show a banner
    }
    return render(request, "user/search_results.html", context)

def upload_prescription(request, id):
    if request.method == "POST":
        uid = request.session['uid']
        user = Register.objects.get(id=uid)
        med = Medicine.objects.get(id=id)
        img = request.FILES.get('image')  # Make sure input name in HTML is 'image'

        # Create the prescription record
        Prescription.objects.create(
            user=user,
            medicine=med,
            image=img,
            status='Pending'
        )

        # Go back to the product page
        return redirect(f'/shop/{id}/')


def view_prescriptions(request):
    # Filter: Status is Pending AND Medicine is NOT empty
    pres_list = Prescription.objects.filter(status='Pending', medicine__isnull=False)
    return render(request, "pharmacist/view_prescriptions.html", {'pres_list': pres_list})


def view_general_prescriptions(request):
    # Filter: Status is Pending AND Medicine IS empty
    pres_list = Prescription.objects.filter(status='Pending', medicine__isnull=True)
    return render(request, "pharmacist/view_general_requests.html", {'pres_list': pres_list})

def approve_prescription(request, id):
        pres = Prescription.objects.get(id=id)
        pres.status = 'Approved'
        pres.save()
        return redirect('/view_prescriptions/')

def reject_prescription(request, id):
        pres = Prescription.objects.get(id=id)
        pres.status = 'Rejected'
        pres.save()
        return redirect('/view_prescriptions/')


def upload_general(request):
    if 'uid' not in request.session:
        return redirect('/login/')

        # 2. Get User (So we can pass it to template if needed)
    uid = request.session['uid']
    user = Register.objects.get(id=uid)
    if request.method == "POST":
        if 'uid' in request.session:
            uid = request.session['uid']
            user = Register.objects.get(id=uid)

            # 1. Get Inputs
            img = request.FILES.get('image')
            pincode = request.POST.get('pincode')
            delivery_type = request.POST.get('delivery_type')  # 'Home' or 'Pickup'
            notes = request.POST.get('notes')

            if img and pincode:
                # --- SMART ASSIGNMENT LOGIC ---

                # A. Find pharmacies that serve this pincode AND are active
                # We use icontains to find "682001" inside "682001, 682005"
                potential_pharmacies = Pharmacy.objects.filter(
                    service_pincodes__icontains=pincode,
                    is_active=True
                )

                assigned_to = None

                if potential_pharmacies.exists():
                    # B. LOAD BALANCING (The "Fastest" Logic)
                    # Count how many 'Pending' or 'Assigned' prescriptions each pharmacy has.
                    # Order them by workload (Lowest first).
                    best_pharmacy = potential_pharmacies.annotate(
                        workload=Count('prescription',
                                       filter=Q(prescription__status__in=['Uploaded', 'Assigned to Pharmacy']))
                    ).order_by('workload').first()

                    assigned_to = best_pharmacy
                else:
                    # Fallback: If no pharmacy matches pincode, assign to Head Office (ID 1)
                    # or leave None (Admin will assign later)
                    assigned_to = Pharmacy.objects.first()

                # C. Create Prescription Ticket
                Prescription.objects.create(
                    user=user,
                    medicine=None,  # General upload
                    image=img,
                    status='Assigned to Pharmacy',  # Step 2 of Master Plan
                    assigned_pharmacy=assigned_to,
                    delivery_type=delivery_type,
                    user_note=notes
                    # Storing user notes here temporarily or add a new field
                )

                return redirect('/user/')
        else:
            return redirect('/login/')

    return render(request, "user/upload_general.html")

@never_cache
def delivery_home(request):
    if 'did' in request.session:
        did = request.session['did']
        agent = get_object_or_404(DeliveryAgent, id=did) # <--- THIS IS CRITICAL

        # 1. New Tasks
        new_tasks = Order.objects.filter(
            assigned_agent=agent,
            status='Out for Pickup'
        ).order_by('-created_at')

        # 2. Active Deliveries
        active_deliveries = Order.objects.filter(
            assigned_agent=agent,
            status='Out for Delivery'
        ).order_by('-created_at')

        # 3. History
        history = Order.objects.filter(
            assigned_agent=agent,
            status='Delivered'
        ).order_by('-created_at')[:10]

        context = {
            'agent': agent, # <--- Sending the data to HTML
            'new_tasks': new_tasks,
            'active_deliveries': active_deliveries,
            'history': history
        }
        return render(request, "delivery_agent/delivery_home.html", context)
    else:
        return redirect('/login/')

@never_cache
def pharmacies(request):
    us=Pharmacy.objects.all()
    return render(request, "admin/pharmacies.html",{"us":us})

def editpharmacy(request,id):
    phar = get_object_or_404(Pharmacy, id=id)

    if request.method == 'POST':

        new_name = request.POST.get('name')
        new_location = request.POST.get('location')
        new_address = request.POST.get('email')
        new_contact = request.POST.get('phone')
        new_email = request.POST.get('email')
        new_service_pincodes = request.POST.get('service_pincodes')

        phar.name = new_name
        phar.location = new_location
        phar.address = new_address
        phar.contact = new_contact
        phar.email = new_email
        phar.service_pincodes = new_service_pincodes

        phar.save()

        return redirect("/pharmacies/")

    else:

        context = {
            'phar': phar
        }
        return render(request, 'admin/edit_pharmacy.html', context)

def addpharmacy(request):
    if request.method == 'POST':
        n = request.POST.get('name')
        loc = request.POST.get('location')
        add = request.POST.get('address')
        c = request.POST.get('contact')
        e = request.POST.get("email")
        s = request.POST.get("service")
        p = request.POST.get('password')

        pharmacy = Pharmacy(
            name=n,
            location=loc,
            address=add,
            contact=c,
            email=e,
            password=p,
            service_pincodes=s,

        )
        pharmacy.save()
        return redirect("/pharmacies/")

    return render(request, 'admin/add_pharmacy.html')

def blockpharmacy(request, id):
    pharmacy = get_object_or_404(Pharmacy, id=id)
    pharmacy.is_active = False
    pharmacy.save()
    return redirect("/pharmacies/")

def unblockpharmacy(request, id):
    pharmacy = get_object_or_404(Pharmacy, id=id)
    pharmacy.is_active = True
    pharmacy.save()
    return redirect("/pharmacies/")

@never_cache
def admin_products(request):
    products = Medicine.objects.all().order_by('-id')
    categories = Category.objects.all()
    pharmacies = Pharmacy.objects.all()


    context = {
        "products": products,
        "categories": categories,
        "pharmacies": pharmacies,

    }
    return render(request, "admin/products.html", context)



def lock_and_process(request, id):
    if 'pharmacy_id' in request.session:
        pid = request.session['pharmacy_id']
        my_pharmacy = get_object_or_404(Pharmacy, id=pid)
        pres = get_object_or_404(Prescription, id=id)

        # 1. Check Lock (Compare Pharmacy Objects)
        if pres.locked_by_pharmacy and pres.locked_by_pharmacy != my_pharmacy:
            return redirect('/pharmacist/')

        # 2. Apply Lock
        if pres.locked_by_pharmacy != my_pharmacy:
            pres.locked_by_pharmacy = my_pharmacy
            pres.status = 'Under Review'
            pres.save()

        return redirect(f'/process_prescription/{id}/')
    return redirect('/login/')


def process_prescription(request, id):
    if 'pharmacy_id' in request.session:
        pid = request.session['pharmacy_id']
        staff_name = request.session.get('staff_name', 'Staff')
        my_pharmacy = get_object_or_404(Pharmacy, id=pid)
        pres = get_object_or_404(Prescription, id=id)

        # Security Check
        if pres.locked_by_pharmacy != my_pharmacy:
            return redirect('/pharmacist/')

        # CHANGED: Filter inventory by Pharmacy
        my_inventory = Medicine.objects.filter(added_by_pharmacy=my_pharmacy)

        query = request.GET.get('search_med')
        if query:
            my_inventory = my_inventory.filter(name__icontains=query)

        added_items = PrescriptionItem.objects.filter(prescription=pres)
        total_cost = sum(item.total_price for item in added_items)

        # Transfer logic
        other_pharmacies = Pharmacy.objects.filter(is_active=True).exclude(id=my_pharmacy.id)

        context = {
            'pres': pres,
            'customer': pres.user,
            'inventory': my_inventory,
            'added_items': added_items,
            'total_cost': total_cost,
            'other_pharmacies': other_pharmacies,
            'staff_name': staff_name
        }
        return render(request, "pharmacist/process_prescription.html", context)
    else:
        return redirect('/login/')


def add_pres_item(request, pres_id):
    if 'pid' in request.session:
        if request.method == "POST":
            med_id = request.POST.get('medicine_id')
            qty = int(request.POST.get('quantity'))

            pres = get_object_or_404(Prescription, id=pres_id)
            med = get_object_or_404(Medicine, id=med_id)

            # Create or Update Item in Special Cart
            item, created = PrescriptionItem.objects.get_or_create(
                prescription=pres,
                medicine=med,
                defaults={'quantity': qty, 'price_at_time': med.price}
            )

            if not created:
                item.quantity += qty
                item.save()

            # Update Master Total
            pres.estimated_total += (med.price * qty)
            pres.save()

            return redirect(f'/process_prescription/{pres_id}/')
    return redirect('/login/')


def remove_pres_item(request, item_id):
    if 'pid' in request.session:
        # 1. Get the item to be deleted
        item = get_object_or_404(PrescriptionItem, id=item_id)

        # 2. Get the parent prescription (to update the total cost)
        pres = item.prescription

        # 3. Update the estimated total
        # We subtract this item's price from the total
        pres.estimated_total -= item.total_price
        pres.save()

        # 4. Delete the item
        item.delete()

        # 5. Refresh the page
        return redirect(f'/process_prescription/{pres.id}/')
    return redirect('/login/')


def submit_to_user(request, pres_id):
    if 'pharmacy_id' in request.session:
        staff_name = request.session.get('staff_name', 'Staff')
        pres = get_object_or_404(Prescription, id=pres_id)
        note = request.POST.get('pharmacist_note')

        pres.status = 'Awaiting User Confirmation'
        pres.pharmacist_note = note

        # CHANGED: Save the text name
        pres.handled_by_name = staff_name

        # Unlock
        pres.locked_by_pharmacy = None
        pres.save()

        return redirect('/pharmacist/')
    return redirect('/login/')


def my_prescriptions(request):
    if 'uid' in request.session:
        uid = request.session['uid']
        user = Register.objects.get(id=uid)

        # Fetch all prescriptions uploaded by this user
        pres_list = Prescription.objects.filter(user=user).order_by('-created_at')

        return render(request, "user/my_prescriptions.html", {'pres_list': pres_list})
    return redirect('/login/')


def review_prescription(request, id):
    if 'uid' in request.session:
        pres = get_object_or_404(Prescription, id=id)

        # Security: Ensure this prescription belongs to the logged-in user
        if pres.user.id != request.session['uid']:
            return redirect('/user/')

        # Get the items added by the pharmacist
        items = PrescriptionItem.objects.filter(prescription=pres)

        # Calculate totals
        subtotal = sum(item.total_price for item in items)
        delivery_fee = 50.00 if pres.delivery_type == 'Home' else 0.00
        grand_total = float(subtotal) + delivery_fee

        context = {
            'pres': pres,
            'items': items,
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'grand_total': grand_total
        }
        return render(request, "user/review_prescription.html", context)
    return redirect('/login/')


def confirm_prescription_order(request, id):
    if 'uid' in request.session:
        pres = get_object_or_404(Prescription, id=id)

        if request.method == "POST":
            address = request.POST.get('address')
            city = request.POST.get('city')
            zip_code = request.POST.get('zip')
            payment_mode = request.POST.get('payment_mode')

            group_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

            pres.status = 'Confirmed'
            pres.save()

            items = PrescriptionItem.objects.filter(prescription=pres)

            for item in items:
                Order.objects.create(
                    user=pres.user,
                    medicine=item.medicine,
                    quantity=item.quantity,
                    fname=pres.user.fname,
                    address=f"{address}, {city}",
                    zip=zip_code,
                    assigned_pharmacy=pres.assigned_pharmacy,
                    status='Confirmed',

                    # 1. FIX: Use 'processed_by_name' and fetch string from prescription
                    processed_by_name=pres.handled_by_name,

                    notes=f"Generated from Prescription #{pres.id}",
                    order_group_id=group_id,
                    payment_mode=payment_mode
                )

                item.medicine.quantity -= item.quantity
                item.medicine.save()

            return redirect('/thanku/')

    return redirect('/user/')


def mark_processed(request, pres_id):
    if 'pid' in request.session:
        # Get the prescription
        pres = get_object_or_404(Prescription, id=pres_id)

        if request.method == "POST":
            action = request.POST.get('action')

            if action == 'reject':
                pres.status = 'Rejected'

                # IMPORTANT: Release the lock so it's closed properly
                pres.locked_by = None

                # Optional: Save the reason if you have a field for it
                # pres.rejection_reason = "Rejected by pharmacist"

                pres.save()

        return redirect('/pharmacist/')  # Back to dashboard
    return redirect('/login/')


def transfer_prescription(request, id):
    # 1. FIX: Use 'pharmacy_id'
    if 'pharmacy_id' in request.session:
        pid = request.session['pharmacy_id']

        # 2. FIX: Get Pharmacy directly
        current_pharmacy = get_object_or_404(Pharmacy, id=pid)
        current_pharmacy_id = str(current_pharmacy.id)

        pres = get_object_or_404(Prescription, id=id)

        if request.method == 'POST':
            new_pharmacy_id = request.POST.get('new_pharmacy_id')
            new_pharmacy = Pharmacy.objects.get(id=new_pharmacy_id)

            pres.assigned_pharmacy = new_pharmacy
            pres.status = 'Assigned to Pharmacy'

            # 3. FIX: Unlock using the Pharmacy Field
            pres.locked_by_pharmacy = None

            if pres.previous_pharmacies:
                pres.previous_pharmacies += f",{current_pharmacy_id}"
            else:
                pres.previous_pharmacies = current_pharmacy_id

            pres.save()

            return redirect('/pharmacist/')

    return redirect('/login/')

def reject_quote(request, id):
    if 'uid' in request.session:
        pres = get_object_or_404(Prescription, id=id)
        pres.status = 'Rejected by User'
        pres.save()
        return redirect('/my_prescriptions/')
    return redirect('/login/')


def process_order_action(request, id):
    if 'pharmacy_id' in request.session:
        staff_name = request.session.get('staff_name', 'Staff')  # Get name from session
        order = get_object_or_404(Order, id=id)

        if request.method == "POST":
            action = request.POST.get('action')

            if action == 'approve':
                if order.medicine.quantity >= order.quantity:
                    order.medicine.quantity -= order.quantity
                    order.medicine.save()
                    order.status = 'Packed'

                    # CHANGED: Save the text name
                    order.processed_by_name = staff_name
                    order.save()

            elif action == 'reject':
                order.status = 'Rejected'
                order.processed_by_name = staff_name
                order.save()
                assign_driver_to_order(order)

        return redirect('/pharmacist/')
    return redirect('/login/')


def process_group_order(request, group_id):
    # 1. FIX: Check correct session
    if 'pharmacy_id' in request.session:
        pid = request.session['pharmacy_id']
        staff_name = request.session.get('staff_name', 'Staff')

        # 2. FIX: Get Pharmacy Object
        my_pharmacy = get_object_or_404(Pharmacy, id=pid)

        group_orders = Order.objects.filter(
            order_group_id=group_id,
            assigned_pharmacy=my_pharmacy,
            status__in=['Pending', 'Confirmed']
        )

        if request.method == "POST":
            action = request.POST.get('action')

            if action == 'approve_all':
                for order in group_orders:
                    if order.medicine.quantity >= order.quantity:
                        order.medicine.quantity -= order.quantity
                        order.medicine.save()

                        order.status = 'Packed'
                        # 3. FIX: Save Staff Name (String)
                        order.processed_by_name = staff_name
                        order.save()
                        assign_driver_to_order(order)

                        # 4. FIX: History uses string name
                        OrderHistory.objects.create(
                            order=order,
                            status='Packed',
                            description=f"Group Pack by {staff_name}",
                            action_by=f"Staff: {staff_name}"
                        )

            elif action == 'reject_all':
                for order in group_orders:
                    order.status = 'Rejected'
                    order.processed_by_name = staff_name
                    order.save()

                    OrderHistory.objects.create(
                        order=order,
                        status='Rejected',
                        description="Group Reject",
                        action_by=f"Staff: {staff_name}"
                    )

        return redirect('/pharmacist/')
    return redirect('/login/')


def pharmacy_staff_login(request):
    # Security: Ensure they actually logged in as a pharmacy first
    if 'pharmacy_id' not in request.session:
        return redirect('/login/')

    # Get Pharmacy details to show on screen (e.g. "Login to City Meds")
    pid = request.session['pharmacy_id']
    pharmacy = Pharmacy.objects.get(id=pid)

    if request.method == "POST":
        staff_name = request.POST.get("staff_name")

        if staff_name:
            # 3. Save the name to session
            request.session['staff_name'] = staff_name
            # 4. Final Redirect to Dashboard
            return redirect("/pharmacist")

    return render(request, "pharmacy_staff_login.html", {'pharmacy': pharmacy})


def update_pincode(request):
    if request.method == "POST":
        pincode = request.POST.get('pincode')

        # 1. Save to Session (Used for filtering search results)
        request.session['user_pincode'] = pincode

        # 2. Save to Database (If user is logged in)
        if 'uid' in request.session:
            user = Register.objects.get(id=request.session['uid'])
            user.zip = pincode
            user.save()

        # Redirect back to the page they came from (or Home)
        return redirect(request.META.get('HTTP_REFERER', '/user/'))

    return redirect('/user/')


def pharmacy_inventory(request):
    if 'pharmacy_id' in request.session:
        pid = request.session['pharmacy_id']
        my_pharmacy = get_object_or_404(Pharmacy, id=pid)
        staff_name = request.session.get('staff_name', 'Staff')

        # 1. Base Query
        medicines = Medicine.objects.filter(added_by_pharmacy=my_pharmacy).order_by('-id')
        categories = Category.objects.all()

        # 2. Filtering Logic
        query = request.GET.get('q')
        cat_filter = request.GET.get('category')
        stock_filter = request.GET.get('stock')

        if query:
            medicines = medicines.filter(name__icontains=query)

        if cat_filter and cat_filter != 'all':
            medicines = medicines.filter(category__id=cat_filter)

        if stock_filter == 'low':
            medicines = medicines.filter(quantity__lt=10)
        elif stock_filter == 'out':
            medicines = medicines.filter(quantity=0)

        # 3. Stats for Top Bar
        total_meds = medicines.count()
        low_stock_count = medicines.filter(quantity__lt=10).count()
        out_of_stock_count = medicines.filter(quantity=0).count()

        context = {
            'pharmacy': my_pharmacy,
            'staff_name': staff_name,
            'medicines': medicines,
            'categories': categories,
            'stats': {
                'total': total_meds,
                'low': low_stock_count,
                'out': out_of_stock_count
            }
        }
        return render(request, "pharmacist/inventory.html", context)
    return redirect('/login/')


def update_inventory(request, id):
    if 'pharmacy_id' in request.session:
        pid = request.session['pharmacy_id']
        my_pharmacy = get_object_or_404(Pharmacy, id=pid)
        med = get_object_or_404(Medicine, id=id)

        # Security: Ensure this pharmacy owns this medicine
        if med.added_by_pharmacy != my_pharmacy:
            return redirect('/inventory/')

        if request.method == "POST":
            new_price = request.POST.get('price')
            new_qty = request.POST.get('quantity')

            med.price = new_price
            med.quantity = new_qty
            med.save()

        return redirect('/inventory/')
    return redirect('/login/')


def delete_medicine(request, id):
    if 'pharmacy_id' in request.session:
        pid = request.session['pharmacy_id']
        my_pharmacy = get_object_or_404(Pharmacy, id=pid)
        med = get_object_or_404(Medicine, id=id)

        if med.added_by_pharmacy == my_pharmacy:
            med.delete()

        return redirect('/inventory/')
    return redirect('/login/')


def assign_driver_to_order(order):

    # 1. Get the location of the Pharmacy
    pharmacy_location = order.assigned_pharmacy.location

    # 2. Find Agents who are:
    #    a) In the same location
    #    b) Marked as 'Available'
    candidates = DeliveryAgent.objects.filter(
        current_location__icontains=pharmacy_location,
        is_available=True
    )

    if candidates.exists():
        # 3. Load Balancing: Find the agent with the fewest active jobs
        # We count orders that are 'Out for Pickup' or 'Out for Delivery'
        best_agent = candidates.annotate(
            active_load=Count('order', filter=Q(order__status__in=['Out for Pickup', 'Out for Delivery']))
        ).order_by('active_load').first()

        # 4. Assign the Agent
        order.assigned_agent = best_agent

        # 5. Update Status: It moves from 'Packed' -> 'Out for Pickup'
        order.status = 'Out for Pickup'
        order.save()

        # Log it
        OrderHistory.objects.create(
            order=order,
            status='Out for Pickup',
            description=f"Auto-assigned to agent: {best_agent.name}",
            action_by="System"
        )
        return True

    return False  # No agent found


def my_orders(request):
    if 'uid' in request.session:
        uid = request.session['uid']
        user = Register.objects.get(id=uid)

        # 1. Fetch raw rows
        raw_orders = Order.objects.filter(user=user).order_by('-created_at')

        # 2. Grouping Logic
        # We will create a list of dictionaries, where each dictionary is one "Shipment"
        grouped_orders = {}

        for order in raw_orders:
            # Use Group ID. If missing (old data), make a unique fake ID
            group_key = order.order_group_id if order.order_group_id else f"ORD-{order.id}"

            if group_key not in grouped_orders:
                # Initialize the Group
                grouped_orders[group_key] = {
                    'group_id': group_key,
                    'date': order.created_at,
                    'status': order.status,
                    'pharmacy': order.assigned_pharmacy.name if order.assigned_pharmacy else "Processing",
                    'items': [],
                    'grand_total': 0,
                    'delivery_agent': order.assigned_agent
                }

            # Calculate Item Total
            item_total = order.quantity * order.medicine.price

            # Add item to the list
            grouped_orders[group_key]['items'].append({
                'name': order.medicine.name,
                'image': order.medicine.image,
                'qty': order.quantity,
                'price': order.medicine.price,
                'total': item_total
            })

            # Add to Grand Total
            grouped_orders[group_key]['grand_total'] += item_total

        # Convert dict values to a list to send to template
        context = {
            'orders': list(grouped_orders.values())
        }
        return render(request, "user/my_orders.html", context)

    return redirect('/login/')


def track_order(request, group_id):
    if 'uid' in request.session:
        uid = request.session['uid']
        user = Register.objects.get(id=uid)

        # 1. Get the orders in this group (to get current status & agent)
        orders = Order.objects.filter(order_group_id=group_id, user=user)

        if not orders.exists():
            return redirect('/my_orders/')

        # We take the first item to represent the whole shipment status
        main_order = orders.first()

        # 2. Get the Timeline (History)
        # We fetch history for ONE item in the group (since they move together)
        history = OrderHistory.objects.filter(order=main_order).order_by('-timestamp')

        context = {
            'order': main_order,
            'history': history,
            'item_count': orders.count()
        }
        return render(request, "user/track_order.html", context)
    return redirect('/login/')


def delivery_update_status(request, id):
    if 'did' in request.session:
        agent_id = request.session['did']
        agent = get_object_or_404(DeliveryAgent, id=agent_id)
        order = get_object_or_404(Order, id=id)

        if request.method == "POST":
            action = request.POST.get('action')

            if action == 'pickup':
                # Agent has arrived at Pharmacy and taken the package
                order.status = 'Out for Delivery'
                order.save()

                # Log History
                OrderHistory.objects.create(
                    order=order,
                    status='Out for Delivery',
                    description=f"Picked up from {order.assigned_pharmacy.name}",
                    action_by=f"Agent: {agent.name}"
                )

            elif action == 'deliver':
                # Agent has handed over to Customer
                order.status = 'Delivered'

                # If COD, we assume cash is collected here
                if order.payment_mode == 'COD':
                    # Optional: order.payment_status = 'Paid'
                    pass

                order.save()

                # Log History
                OrderHistory.objects.create(
                    order=order,
                    status='Delivered',
                    description="Delivered successfully",
                    action_by=f"Agent: {agent.name}"
                )

        return redirect('/delivery_home/')
    return redirect('/login/')


def toggle_agent_status(request):
    if 'did' in request.session:
        agent = get_object_or_404(DeliveryAgent, id=request.session['did'])

        # Flip the status
        agent.is_available = not agent.is_available
        agent.save()

        return redirect('/delivery_home/')
    return redirect('/login/')


# 1. ASK EMAIL & SEND OTP
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # Check if email exists in ANY of your 3 tables
        user = Register.objects.filter(email=email).first()
        pharmacy = Pharmacy.objects.filter(email=email).first()
        agent = DeliveryAgent.objects.filter(email=email).first()

        target_user = user or pharmacy or agent

        if target_user:
            # Generate 4-digit OTP
            otp = str(random.randint(1000, 9999))

            # Save data to Session (Temporary storage)
            request.session['reset_email'] = email
            request.session['reset_otp'] = otp

            # Determine user type for later updating
            if user:
                request.session['user_type'] = 'user'
            elif pharmacy:
                request.session['user_type'] = 'pharmacy'
            elif agent:
                request.session['user_type'] = 'agent'

            # Send Email
            subject = "CureVia Password Reset OTP"
            message = f"Hello,\n\nYour OTP to reset your password is: {otp}\n\nDo not share this with anyone."
            from_email = f"CureVia Support <{settings.EMAIL_HOST_USER}>"
            recipient_list = [email]

            try:
                send_mail(subject, message, from_email, recipient_list)
                return redirect('/verify_otp/')
            except Exception as e:
                return render(request, "forgot_password.html", {"msg": "Error sending email. Check internet."})
        else:
            return render(request, "forgot_password.html", {"msg": "Email not registered with us."})

    return render(request, "forgot_password.html")


# 2. VERIFY THE OTP
def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        generated_otp = request.session.get('reset_otp')

        if entered_otp == generated_otp:
            return redirect('/new_password/')
        else:
            return render(request, "verify_otp.html", {"msg": "Invalid OTP. Try again."})

    return render(request, "verify_otp.html")


# 3. SET NEW PASSWORD
def new_password(request):
    if request.method == "POST":
        new_pass = request.POST.get("new_password")
        confirm_pass = request.POST.get("confirm_password")

        email = request.session.get('reset_email')
        user_type = request.session.get('user_type')

        if new_pass == confirm_pass:
            # Update the password in the correct table
            if user_type == 'user':
                Register.objects.filter(email=email).update(password=new_pass)
            elif user_type == 'pharmacy':
                Pharmacy.objects.filter(email=email).update(password=new_pass)
            elif user_type == 'agent':
                DeliveryAgent.objects.filter(email=email).update(password=new_pass)

            # Clean up session
            del request.session['reset_otp']
            del request.session['reset_email']

            return redirect('/login/')
        else:
            return render(request, "new_password.html", {"msg": "Passwords do not match."})

    return render(request, "new_password.html")

@never_cache
def admin_orders(request):
    # Base Query
    orders = Order.objects.all().order_by('-created_at')

    # Optional: Simple Search Filter (by Order ID or Customer Name)
    query = request.GET.get('q')
    if query:
        orders = orders.filter(
            Q(order_group_id__icontains=query) |
            Q(fname__icontains=query)
        )

    context = {
        'orders': orders,
        'query': query
    }
    return render(request, "admin/admin_orders.html", context)

@never_cache
def admin_delivery_agents(request):
    agents = DeliveryAgent.objects.all()
    return render(request, "admin/delivery_agents.html", {"agents": agents})


def add_delivery_agent(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        location = request.POST.get('location')  # e.g. "Kochi"

        DeliveryAgent.objects.create(
            name=name,
            email=email,
            phone=phone,
            password=password,
            current_location=location,
            is_available=True
        )
        return redirect('/delivery_agents/')

    return render(request, "admin/add_delivery_agent.html")


def edit_delivery_agent(request, id):
    agent = get_object_or_404(DeliveryAgent, id=id)

    if request.method == "POST":
        agent.name = request.POST.get('name')
        agent.email = request.POST.get('email')
        agent.phone = request.POST.get('phone')
        agent.current_location = request.POST.get('location')
        # agent.is_available = request.POST.get('is_available') == 'on'
        agent.save()
        return redirect('/delivery_agents/')

    return render(request, "admin/edit_delivery_agent.html", {'agent': agent})


def delete_delivery_agent(request, id):
    agent = get_object_or_404(DeliveryAgent, id=id)
    agent.delete()
    return redirect('/delivery_agents/')

def block_agent(request, id):
    agent = get_object_or_404(DeliveryAgent, id=id)
    agent.is_available = False # Force offline
    agent.save()
    return redirect('/delivery_agents/')

def unblock_agent(request, id):
    agent = get_object_or_404(DeliveryAgent, id=id)
    agent.is_available = True # Force online (or allow login)
    agent.save()
    return redirect('/delivery_agents/')


def logout(request):
    # --- SPECIAL LOGIC FOR DELIVERY AGENTS ---
    if 'did' in request.session:
        try:
            # Find the agent and set them to Offline
            agent = DeliveryAgent.objects.get(id=request.session['did'])
            agent.is_available = False
            agent.save()
        except DeliveryAgent.DoesNotExist:
            pass  # Continue logging out even if agent not found

    # --- UNIVERSAL LOGOUT (For Everyone) ---
    # This deletes 'uid', 'pharmacy_id', 'user_id', 'staff_name', etc.
    request.session.flush()

    return redirect('/login/')