from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
import uuid
from .models import *

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
        log = Register.objects.filter(email=e, password=p)
        plog=Pharmacist.objects.filter(email=e, password=p)
        dlog=DeliveryAgent.objects.filter(email=e, password=p)
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
                r = i.rights
                if r == "pharmacist":
                    request.session['pid']=i.id
                    return redirect("/pharmacist")
        elif dlog:
            for i in dlog:
                request.session['did'] = i.id
                return redirect("/delivery_home")

        else:
            msg = True
    return render(request, "login.html",{"msg":msg})

def user(request):
    if 'user_id' in request.session:
        uid = request.session['user_id']
        current_user = get_object_or_404(Register, id=uid)
        popular_products = Medicine.objects.filter(is_popular=True)
        new_products = Medicine.objects.all().order_by('-id')[:6]
        return render(request, "user/userhome.html", {'user': current_user, 'products': popular_products,'new_products': new_products})
    else:
        return redirect("/login")

def admin(request):
    return render(request, "admin/adminhome.html")

def pharmacist(request):
    if 'pid' in request.session:
        pid = request.session['pid']
        # 1. Get Logged in Pharmacist
        pharmacist = get_object_or_404(Pharmacist, id=pid)
        my_pharmacy = pharmacist.pharmacy

        if not my_pharmacy:
            return render(request, "pharmacist/no_pharmacy_error.html")

        # 2. Get Pending Prescriptions (The Images)
        # We fetch 'Assigned' (New) OR 'Under Review' (Locked by someone)
        pending_prescriptions = Prescription.objects.filter(
            assigned_pharmacy=my_pharmacy,
            status__in=['Assigned to Pharmacy', 'Under Review']
        ).order_by('-created_at')

        # 3. Get Pending Orders (The Cart Checkouts)
        pending_orders = Order.objects.filter(
            assigned_pharmacy=my_pharmacy,
            status__in=['Pending', 'Packed', 'Confirmed']
        ).order_by('order_group_id', '-created_at')

        # 4. Low Stock Check
        low_stock_meds = Medicine.objects.filter(
            added_by__pharmacy=my_pharmacy,
            quantity__lt=10
        )

        context = {
            'pharmacist': pharmacist,
            'pharmacy': my_pharmacy,
            'pending_prescriptions': pending_prescriptions, # List for Table 1
            'pending_orders': pending_orders,               # List for Table 2
            'low_stock_meds': low_stock_meds,
        }
        return render(request, "pharmacist/pharhome.html", context)
    else:
        return redirect('/login/')

def customer(request):
    us=Register.objects.exclude(rights='admin')
    return render(request, "admin/customer.html",{"us":us})

def blockuser(request,id):
    Register.objects.filter(id=id).update(rights='Blocked')
    return redirect("/customer/")

def unblock(request,id):
    Register.objects.filter(id=id).update(rights='user')
    return redirect("/customer/")

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

def pharmacists(request):
    us=Pharmacist.objects.all()
    return render(request, "admin/pharmacist.html",{"us":us})

def editphar(request,id):
    phar = get_object_or_404(Pharmacist, id=id)

    if request.method == 'POST':

        new_fname = request.POST.get('fname')
        new_lname = request.POST.get('lname')
        new_email = request.POST.get('email')
        new_phone = request.POST.get('phone')

        phar.fname = new_fname
        phar.lname = new_lname
        phar.email = new_email
        phar.phone = new_phone

        phar.save()

        return redirect("/pharmacists/")

    else:

        context = {
            'phar': phar
        }
        return render(request, 'admin/edit_phar.html', context)


def addphar(request):
    if request.method == 'POST':
        f = request.POST.get('fname')
        l = request.POST.get('lname')
        e = request.POST.get('email')
        ph = request.POST.get('phone')
        q = request.POST.get("qualif")
        add = request.POST.get("address")
        lic = request.POST.get("license")
        p = request.POST.get("password")

        pharmacist = Pharmacist(
            fname=f,
            lname=l,
            email=e,
            phone=ph,
            qualif=q,
            address=add,
            license=lic,
            password=p,

        )
        pharmacist.save()
        return redirect("/pharmacists/")

    return render(request, 'admin/add_phar.html')


def blockphar(request, id):
    pharmacist = get_object_or_404(Pharmacist, id=id)
    pharmacist.is_active = False
    pharmacist.save()
    return redirect("/pharmacists/")

def unblockphar(request, id):
    pharmacist = get_object_or_404(Pharmacist, id=id)
    pharmacist.is_active = True
    pharmacist.save()
    return redirect('/pharmacists/')

@login_required
def addmed(request):
    addmed=Category.objects.all()
    pid=request.session['pid']
    ph=Pharmacist.objects.get(id=pid)
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

        c=Category.objects.get(id=c)
        Medicine.objects.create(
            name=n,
            category=c,
            purpose=p,
            description=d,
            price=pr,
            quantity=q,
            rx_required=rx,
            expiry_date=ex,
            image=i,
            added_by=ph
        )

        return redirect("/addmed/")

    return render(request,'pharmacist/add_medicine.html',{'addmed':addmed} )

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

def forgotpass(request):
    return render(request, "forgot_password.html")


def search_product(request):
    query = request.GET.get('q')
    products = []

    if query:
        products = Medicine.objects.filter(
            Q(name__icontains=query) |
            Q(purpose__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()  # distinct() prevents duplicates if a keyword matches both name and category

    context = {
        'products': products,
        'query': query
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


def delivery_home(request):
    return render(request, "delivery_agent/delivery_home.html")

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

        pharmacy = Pharmacy(
            name=n,
            location=loc,
            address=add,
            contact=c,
            email=e,
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


def admin_products(request):
    products = Medicine.objects.all().order_by('-id')
    categories = Category.objects.all()
    pharmacies = Pharmacy.objects.all()
    pharmacists = Pharmacist.objects.all()

    context = {
        "products": products,
        "categories": categories,
        "pharmacies": pharmacies,
        "pharmacists": pharmacists,
    }
    return render(request, "admin/products.html", context)

from django.utils import timezone

def lock_and_process(request, id):
    if 'pid' in request.session:
        pid = request.session['pid']
        pharmacist = Pharmacist.objects.get(id=pid)
        pres = get_object_or_404(Prescription, id=id)

        # 1. CHECK LOCK STATUS
        # If locked by someone else...
        if pres.locked_by and pres.locked_by != pharmacist:
            # You can show an error page, or just redirect back with a message
            # For now, simple redirect back
            return redirect('/pharmacist/')

        # 2. APPLY LOCK (If not already locked by me)
        if pres.locked_by != pharmacist:
            pres.locked_by = pharmacist
            pres.locked_at = timezone.now()
            pres.status = 'Under Review' # Step 3 of Master Plan
            pres.save()

        # 3. Redirect to the Workspace
        return redirect(f'/process_prescription/{id}/')
    return redirect('/login/')


def process_prescription(request, id):
    if 'pid' in request.session:
        pid = request.session['pid']
        pharmacist = Pharmacist.objects.get(id=pid)
        pres = get_object_or_404(Prescription, id=id)

        # Security: Ensure this pharmacist owns the lock!
        if pres.locked_by != pharmacist:
            return redirect('/pharmacist/')

        # 1. Get Inventory
        my_inventory = Medicine.objects.filter(added_by__pharmacy=pharmacist.pharmacy)
        query = request.GET.get('search_med')
        if query:
            my_inventory = my_inventory.filter(name__icontains=query)

        # 2. Get SPECIAL CART Items (Items added by pharmacist for this specific order)
        added_items = PrescriptionItem.objects.filter(prescription=pres)

        # Calculate Total for display
        total_cost = sum(item.total_price for item in added_items)

        context = {
            'pres': pres,
            'customer': pres.user,
            'inventory': my_inventory,
            'added_items': added_items,  # <--- NEW LIST
            'total_cost': total_cost
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
    if 'pid' in request.session:
        pid = request.session['pid']
        pharmacist = Pharmacist.objects.get(id=pid)
        pres = get_object_or_404(Prescription, id=pres_id)
        note = request.POST.get('pharmacist_note')
        # Change status so User sees it
        pres.status = 'Awaiting User Confirmation'
        pres.pharmacist_note = note
        pres.handled_by = pharmacist

        # Release the Lock (Job done)
        pres.locked_by = None
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
            # 1. Get Form Data
            address = request.POST.get('address')
            city = request.POST.get('city')
            zip_code = request.POST.get('zip')
            payment_mode = request.POST.get('payment_mode')  # 'COD' or 'Online'

            # 2. Generate a Group ID (e.g. "ORD-8392")
            group_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

            # 3. Update Prescription
            pres.status = 'Confirmed'
            pres.save()

            # 4. Create Orders
            items = PrescriptionItem.objects.filter(prescription=pres)

            for item in items:
                Order.objects.create(
                    user=pres.user,
                    medicine=item.medicine,
                    quantity=item.quantity,

                    # Address from Form
                    fname=pres.user.fname,
                    address=f"{address}, {city}",
                    zip=zip_code,

                    # Tracking
                    assigned_pharmacy=pres.assigned_pharmacy,
                    status='Confirmed',
                    processed_by=pres.handled_by,  # Use the permanent field
                    notes=f"Generated from Prescription #{pres.id}",

                    # Grouping & Payment
                    order_group_id=group_id,
                    payment_mode=payment_mode
                )

                # Deduct Stock
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
    if 'pid' in request.session:
        pid = request.session['pid']
        current_pharmacist = Pharmacist.objects.get(id=pid)
        current_pharmacy_id = str(current_pharmacist.pharmacy.id)

        pres = get_object_or_404(Prescription, id=id)

        if request.method == 'POST':
            new_pharmacy_id = request.POST.get('new_pharmacy_id')
            new_pharmacy = Pharmacy.objects.get(id=new_pharmacy_id)

            # 1. Update Assigned Pharmacy
            pres.assigned_pharmacy = new_pharmacy

            # 2. Reset Status (So the new pharmacy sees it as a fresh request)
            pres.status = 'Assigned to Pharmacy'

            # 3. UNLOCK IT (Crucial: otherwise the new pharmacy can't open it)
            pres.locked_by = None
            pres.locked_at = None

            # 4. Add CURRENT pharmacy to history (To prevent looping back)
            if pres.previous_pharmacies:
                pres.previous_pharmacies += f",{current_pharmacy_id}"
            else:
                pres.previous_pharmacies = current_pharmacy_id

            pres.save()

            return redirect('/pharmacist/')  # Back to dashboard

    return redirect('/login/')

def reject_quote(request, id):
    if 'uid' in request.session:
        pres = get_object_or_404(Prescription, id=id)
        pres.status = 'Rejected by User'
        pres.save()
        return redirect('/my_prescriptions/')
    return redirect('/login/')


def process_order_action(request, id):
    if 'pid' in request.session:
        pid = request.session['pid']
        pharmacist = Pharmacist.objects.get(id=pid)
        order = get_object_or_404(Order, id=id)

        if request.method == "POST":
            action = request.POST.get('action')

            if action == 'approve':
                if order.medicine.quantity >= order.quantity:
                    # Deduct Stock
                    order.medicine.quantity -= order.quantity
                    order.medicine.save()

                    order.status = 'Packed'
                    order.processed_by = pharmacist
                    order.save()

            elif action == 'reject':
                order.status = 'Rejected'
                order.processed_by = pharmacist
                order.save()

        return redirect('/pharmacist/')
    return redirect('/login/')


def process_group_order(request, group_id):
    if 'pid' in request.session:
        pid = request.session['pid']
        pharmacist = get_object_or_404(Pharmacist, id=pid)

        # 1. FIX: Include 'Confirmed' in the filter so we find the new orders
        group_orders = Order.objects.filter(
            order_group_id=group_id,
            assigned_pharmacy=pharmacist.pharmacy,
            status__in=['Pending', 'Confirmed']  # <--- Added 'Confirmed'
        )

        if request.method == "POST":
            action = request.POST.get('action')

            if action == 'approve_all':
                for order in group_orders:
                    # Check Stock Logic
                    if order.medicine.quantity >= order.quantity:
                        # Deduct Stock
                        order.medicine.quantity -= order.quantity
                        order.medicine.save()

                        # Update Status
                        order.status = 'Packed'  # Ready for Delivery
                        order.processed_by = pharmacist
                        order.save()

                        # Optional: Add to History
                        OrderHistory.objects.create(
                            order=order,
                            status='Packed',
                            description=f"Group Pack by {pharmacist.fname}",
                            action_by=f"Pharmacist: {pharmacist.fname}"
                        )

            elif action == 'reject_all':
                for order in group_orders:
                    order.status = 'Rejected'
                    order.processed_by = pharmacist
                    order.save()

                    OrderHistory.objects.create(
                        order=order,
                        status='Rejected',
                        description="Group Reject",
                        action_by=f"Pharmacist: {pharmacist.fname}"
                    )

        return redirect('/pharmacist/')
    return redirect('/login/')