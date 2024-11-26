import datetime
from tortoise import Model, fields
from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator




class User(Model):
    id = fields.IntField(pk=True, index=True)
    username = fields.CharField(max_length=20, unique=True, null=False, index=True)
    email = fields.CharField(max_length=200, unique=True, index=True, null=False)
    password = fields.CharField(max_length=100, null=False)
    is_verified = fields.BooleanField(default=False)
    join_date = fields.DatetimeField(auto_now_add=True, default=datetime.datetime.now)


class Business(Model):
    id = fields.IntField(pk=True, index=True, unique=True, null=False)
    business_name = fields.CharField(max_length=20, unique=True, null=False, index=True)
    city = fields.CharField(max_length=100, null=False, default='Unspecified')
    region = fields.CharField(max_length=100, null=False, default='Unspecified')
    business_description = fields.TextField(null=True)
    logo = fields.CharField(max_length=200, null=False, default='default.jpg')
    owner = fields.ForeignKeyField('models.User', related_name='business', on_delete=fields.CASCADE)


class Product(Model):
    id = fields.IntField(pk=True, index=True, unique=True, null=False)
    name = fields.CharField(max_length=100, null=False, index=True)
    category = fields.CharField(max_length=30, index=True)
    original_price = fields.DecimalField(max_digits=12, decimal_places=2, null=False)
    new_price = fields.DecimalField(max_digits=12, decimal_places=2, null=False)
    percentage_discount = fields.IntField(null=False, default=0)
    offer_expiration_date = fields.DateField(default=datetime.date.today)
    product_image = fields.CharField(max_length=200, null=False, default='productDefault.jpg')
    date_published = fields.DatetimeField(auto_now_add=True, default=datetime.datetime.now)
    business = fields.ForeignKeyField('models.Business', related_name='products', on_delete=fields.CASCADE)



user_pydantic = pydantic_model_creator(User, name='User', exclude=('is_verified', ))
user_pydanticIn = pydantic_model_creator(User, name='UserIn', exclude_readonly=True, exclude=('is_verified', 'join_date'))
user_pydanticOut = pydantic_model_creator(User, name='UserOut', exclude=('password', ))

business_pydantic = pydantic_model_creator(Business, name='Business', exclude=('logo', ))
business_pydanticIn = pydantic_model_creator(Business, name='BusinessIn', exclude_readonly=True, exclude=('logo',"id" ))
business_pydanticOut = pydantic_model_creator(Business, name='BusinessOut', exclude=('logo', ))

product_pydantic = pydantic_model_creator(Product, name='Product', exclude=('percentage_discount', 'product_image'))
product_pydanticIn = pydantic_model_creator(
    Product, name='ProductIn', exclude_readonly=True, exclude=('percentage_discount', 'id', 'product_image', 'date_published')
    )
product_pydanticOut = pydantic_model_creator(Product, name='ProductOut', exclude=('percentage_discount', 'product_image','id'))
