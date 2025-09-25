import uuid
from django.db import models
from django.utils.text import slugify

class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('parent', 'slug')]
        indexes = [models.Index(fields=['slug']), models.Index(fields=['parent', 'sort_order'])]
        ordering = ['parent__id', 'sort_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Brand(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, related_name='products', null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.CharField(max_length=200, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)  # default display
    currency = models.CharField(max_length=3, default='INR')
    tax_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # optional

    class Meta:
        indexes = [models.Index(fields=['slug']), models.Index(fields=['is_active', 'is_featured'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/%Y/%m/')
    alt_text = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['sort_order', 'created_at']

class Attribute(TimeStampedModel):
    # e.g., Color, Size, Fabric, Occasion
    name = models.CharField(max_length=60, unique=True)

    def __str__(self):
        return self.name

class AttributeValue(TimeStampedModel):
    attribute = models.ForeignKey(Attribute, related_name='values', on_delete=models.CASCADE)
    value = models.CharField(max_length=80)
    hex_code = models.CharField(max_length=7, blank=True)  # for colors like #ff00aa

    class Meta:
        unique_together = [('attribute', 'value')]

    def __str__(self):
        return f'{self.attribute.name}: {self.value}'

class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    sku = models.CharField(max_length=40, unique=True)
    # Flexible attributes via M2M through a mapping table
    attributes = models.ManyToManyField(AttributeValue, related_name='variants', blank=True)
    mrp_price = models.DecimalField(max_digits=10, decimal_places=2)   # original price
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)  # display price
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    weight_grams = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=['sku']), models.Index(fields=['is_active'])]
        constraints = [
            models.CheckConstraint(check=models.Q(sale_price__gte=0), name='variant_sale_price_nonneg'),
            models.CheckConstraint(check=models.Q(mrp_price__gte=0), name='variant_mrp_price_nonneg'),
        ]

    def __str__(self):
        return f'{self.product.name} ({self.sku})'

class Review(TimeStampedModel):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', related_name='reviews', on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.PositiveSmallIntegerField()  # 1-5
    title = models.CharField(max_length=120, blank=True)
    comment = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    published = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['product', 'rating', 'published'])]
        ordering = ['-created_at']