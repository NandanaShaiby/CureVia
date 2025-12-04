from django.db import models
from django.conf import settings

class Register(models.Model):
    fname = models.CharField(max_length=100)
    lname = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.IntegerField()
    gender = models.CharField(max_length=100)
    dob = models.DateField()
    password = models.CharField(max_length=100)
    rights = models.CharField(max_length=100,default="user")
    def __str__(self):
        return f'{self.fname} {self.lname}'

class Pharmacy(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    address = models.TextField()
    contact = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    service_pincodes = models.TextField(help_text="Enter pincodes separated by comma", default="")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Pharmacist(models.Model):
    fname = models.CharField(max_length=100)
    lname = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=100)
    qualif = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    license = models.CharField(max_length=100)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    password = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    rights = models.CharField(max_length=100,default="pharmacist")
    def __str__(self):
        return f'{self.fname} {self.lname}'


class DeliveryAgent(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    is_available = models.BooleanField(default=True)
    current_location = models.CharField(max_length=100, default="Headquarters")
    password = models.CharField(max_length=100)
    rights = models.CharField(max_length=100, default="delivery")

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Medicine(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='medicines')
    purpose = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    rx_required = models.BooleanField(default=False)
    expiry_date = models.DateField()
    image = models.ImageField(upload_to='medicines/', blank=True, null=True)
    added_by = models.ForeignKey(
       Pharmacist,
        on_delete=models.CASCADE,
        related_name='added_medicines'
    )
    added_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_popular = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Cart(models.Model):
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField()
    user = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
    )
    @property
    def total_price(self):
        return self.quantity * self.medicine.price


class Order(models.Model):
    # Foreign Keys
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    user = models.ForeignKey(Register, on_delete=models.CASCADE)

    # Address & Contact
    fname = models.CharField(max_length=100)
    lname = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField()
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    zip = models.CharField(max_length=20)

    # Transaction Details
    quantity = models.PositiveIntegerField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Tracking
    status = models.CharField(max_length=50, default='Pending')
    assigned_pharmacy = models.ForeignKey(Pharmacy, on_delete=models.SET_NULL, null=True, blank=True)
    processed_by = models.ForeignKey(Pharmacist, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_agent = models.ForeignKey(DeliveryAgent, on_delete=models.SET_NULL, null=True, blank=True)

    # --- THESE ARE THE MISSING FIELDS CAUSING THE ERROR ---
    order_group_id = models.CharField(max_length=100, blank=True, null=True)
    payment_mode = models.CharField(max_length=50, default="COD")

    def __str__(self):
        return f'{self.id} {self.medicine.name}'


class Prescription(models.Model):
    user = models.ForeignKey(Register, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='prescriptions/')
    # Uploaded -> Assigned -> Under Review -> Awaiting Confirmation -> Confirmed/Rejected
    status = models.CharField(max_length=100, default='Uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_pharmacy = models.ForeignKey(Pharmacy, on_delete=models.SET_NULL, null=True, blank=True)
    handled_by = models.ForeignKey(Pharmacist, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='handled_prescriptions')
    # 1. Delivery Choice (For Routing)
    DELIVERY_CHOICES = [('Home', 'Home Delivery'), ('Pickup', 'Store Pickup')]
    delivery_type = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default='Home')

    # 2. Locking Mechanism (Prevents 2 pharmacists from editing same order)
    locked_by = models.ForeignKey(Pharmacist, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='locked_prescriptions')
    locked_at = models.DateTimeField(null=True, blank=True)

    # 3. Communication
    # If rejected or needs info, pharmacist writes here
    rejection_reason = models.TextField(null=True, blank=True)
    pharmacist_note = models.TextField(null=True, blank=True)
    # 4. Cost Estimation (Calculated after pharmacist adds meds)
    estimated_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # 5. History Tracking (To avoid loops in transfer)
    previous_pharmacies = models.TextField(default="", blank=True)
    user_note = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.user.fname} - {self.status}'


class PrescriptionItem(models.Model):
    """
    Stores the medicines the Pharmacist adds to the prescription
    while reviewing the image. User must confirm these later.
    """
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    # Price might change, so we lock the price at the time of addition
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        return self.quantity * self.price_at_time

    def __str__(self):
        return f"{self.medicine.name} (x{self.quantity})"

class OrderHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    action_by = models.CharField(max_length=100, default="System")
    order_group_id = models.CharField(max_length=100, blank=True, null=True)
    payment_mode = models.CharField(max_length=50, default="COD")

    def __str__(self):
        return f"{self.order.id} - {self.status}"