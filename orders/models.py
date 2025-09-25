import uuid
from django.db import models
from django.conf import settings

class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Coupon(TimeStampedModel):
    code = models.CharField(max_length=24, unique=True)
    description = models.CharField(max_length=200, blank=True)
    percent_off = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # e.g., 10.00
    amount_off = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

class Cart(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='carts', null=True, blank=True, on_delete=models.SET_NULL)
    session_key = models.CharField(max_length=40, blank=True)  # for guests
    currency = models.CharField(max_length=3, default='INR')
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'session_key', 'is_active'])]

class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey('catalog.ProductVariant', related_name='cart_items', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [('cart', 'variant')]

class Wishlist(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='wishlists', on_delete=models.CASCADE)
    name = models.CharField(max_length=60, default='Default')

    class Meta:
        unique_together = [('user', 'name')]

class WishlistItem(TimeStampedModel):
    wishlist = models.ForeignKey(Wishlist, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('catalog.Product', related_name='wishlisted_in', on_delete=models.CASCADE)

    class Meta:
        unique_together = [('wishlist', 'product')]

class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING'
        PAID = 'PAID'
        FULFILLED = 'FULFILLED'
        CANCELLED = 'CANCELLED'
        REFUNDED = 'REFUNDED'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', null=True, blank=True, on_delete=models.SET_NULL)
    number = models.CharField(max_length=20, unique=True)  # e.g., ORD-2025-000123
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)

    billing_address = models.ForeignKey('customers.Address', related_name='+', on_delete=models.PROTECT)
    shipping_address = models.ForeignKey('customers.Address', related_name='+', on_delete=models.PROTECT)

    class Meta:
        indexes = [models.Index(fields=['number', 'status'])]

class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('catalog.Product', related_name='+', on_delete=models.PROTECT)
    variant = models.ForeignKey('catalog.ProductVariant', related_name='+', on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=40)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        INITIATED = 'INITIATED'
        AUTHORIZED = 'AUTHORIZED'
        CAPTURED = 'CAPTURED'
        FAILED = 'FAILED'
        REFUNDED = 'REFUNDED'

    order = models.ForeignKey(Order, related_name='payments', on_delete=models.CASCADE)
    provider = models.CharField(max_length=40)  # e.g., razorpay, stripe
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.INITIATED)
    transaction_id = models.CharField(max_length=80, blank=True)
    meta = models.JSONField(default=dict, blank=True)

class Shipment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING'
        SHIPPED = 'SHIPPED'
        DELIVERED = 'DELIVERED'
        RETURNED = 'RETURNED'

    order = models.ForeignKey(Order, related_name='shipments', on_delete=models.CASCADE)
    tracking_number = models.CharField(max_length=60, blank=True)
    carrier = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

class ReturnRequest(TimeStampedModel):
    class Reason(models.TextChoices):
        SIZE_FIT = 'SIZE_FIT'
        DAMAGED = 'DAMAGED'
        NOT_AS_DESCRIBED = 'NOT_AS_DESCRIBED'
        OTHER = 'OTHER'

    order = models.ForeignKey(Order, related_name='returns', on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, related_name='returns', on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=Reason.choices)
    status = models.CharField(max_length=20, default='REQUESTED')  # REQUESTED, APPROVED, REJECTED, COMPLETED
    notes = models.TextField(blank=True)