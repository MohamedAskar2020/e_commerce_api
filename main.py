from fastapi import FastAPI, Request, HTTPException, status, Depends, File, UploadFile
import secrets
from fastapi.responses import HTMLResponse
from tortoise.contrib.fastapi import register_tortoise
from models import *
from authentication import *
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from PIL import Image
# signals:
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from pydantic import BaseModel
from datetime import datetime

# templating:
from fastapi.templating import Jinja2Templates
from emails import *


app = FastAPI()

oath2_schema = OAuth2PasswordBearer(tokenUrl='token')

# static files configuration:
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post('/token')
async def generate_token(request_form: OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {"access_token": token, "token_type": "bearer"}




async def get_current_user(token: str = Depends(oath2_schema)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_aud": False})
        if payload:
            user = await User.get(id=payload.get('id'))
            # return await user_pydantic.from_tortoise_orm(user)
            return await user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')

    # return await user

@app.post('/user/me')
async def user_login(user: user_pydanticIn=Depends(get_current_user)): # type: ignore
    business = await Business.get(owner=user)
    logo = business.logo
    logo_path = "./static/images/business/"+logo
    return {
            "status": "ok",
            "data": {
                "username": user.username,
                "email": user.email,
                "business_name": business.business_name,
                "is_verified": user.is_verified,
                "joined_date": user.join_date.strftime("%b %d %Y"),
                "logo": logo_path
            }
        }


@post_save(User)
async def create_business(
    sender: "Type[User]",
    instance: User,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str]
) -> None:
    if created:
        business_obj = await Business.create(business_name=instance.username, owner=instance)
        await business_pydantic.from_tortoise_orm(business_obj)
        # send the email:
        await send_email([instance.email], instance)
        

        print("Business created")
    else:
        print("Updating business")
    







@app.post('/registration')
async def user_registration(user: user_pydanticIn): # type: ignore
    user_info = user.dict(exclude_unset=True)
    user_info['password'] =get_password_hash(user_info['password'])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        "status": "ok",
        "data": f"Hello {new_user.username} thanks for choosing our services.Please chcek your email inbox and click on the link to confirm your registration."
        }

templates = Jinja2Templates(directory="templates")

@app.get("/verification", response_class=HTMLResponse)
async def email_verification(request: Request, token: str):
    user = await verify_token(token)
    if user and not user.is_verified:
        user.is_verified = True
        await user.save()
        return templates.TemplateResponse(
            "verification.html", 
            {
                "request": request, 
                "username": user.username
            }
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )




@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/uploadfile/profile")
async def create_upload_file(
    file: UploadFile = File(...),
    user: user_pydantic = Depends(get_current_user) # type: ignore
    ):
    FILEPATH = "./static/images/business"
    filename = file.filename
    extension = filename.split(".")[1]
    if extension not in ["png", "jpg"]:
        return {"status": "error", "detail": "File extension not allowed"}

    token_name = secrets.token_hex(10) + "." + extension

    generated_name = "{}-{}.{}".format(user.username, token_name, extension)
    file_content = await file.read()
    with open(FILEPATH + generated_name, "wb") as file:
        file.write(file_content)

    # resize the image
    img = Image.open(FILEPATH + generated_name)
    img = img.resize(size=(200, 200))
    img.save(FILEPATH + generated_name)
    file.close()
    
    business = await Business.get(owner=user)
    owner = await business.owner
    
    if owner == user:
        business.logo = token_name
        await business.save()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Not found",
            headers={"WWW-Authenticate": "Bearer"}

            )
    return { 
            "status": "ok",
            "detail": "File uploaded successfully",
            "filename": generated_name
            }

@app.post("/uploadfile/product/{id}")
async def upload_product_image(
    id: int, 
    file: UploadFile = File(...),
    user: user_pydantic = Depends(get_current_user) # type: ignore
    ):
    FILEPATH = "./static/images/products/"
    filename = file.filename
    extension = filename.split(".")[1]
    if extension not in ["png", "jpg"]:
        return {"status": "error", "detail": "File extension not allowed"}

    token_name = secrets.token_hex(10) + "." + extension

    generated_name = "{}-{}.{}".format(user.username, token_name, extension)
    file_content = await file.read()
    with open(FILEPATH + generated_name, "wb") as file:
        file.write(file_content)

    # resize the image
    img = Image.open(FILEPATH + generated_name)
    img = img.resize(size=(200, 200))
    img.save(FILEPATH + generated_name)
    file.close()
    
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    
    if owner == user:
        product.image = token_name
        await product.save()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return {
            "status": "ok",
            "detail": "File uploaded successfully",
            "filename": generated_name
    }

# CRUD Functions:

@app.post("/products")
async def create_product(
    product: product_pydanticIn, # type: ignore
    user: user_pydantic = Depends(get_current_user) # type: ignore
    ):
    business = await Business.get(owner=user)
    product = product.dict(exclude_unset=True)
    # to avoid div by zero error:
    if product["original_price"] > 0:
        product["percentage_discount"] = ((product["original_price"] - product["new_price"]) / product["original_price"]) * 100

        # get the discount percentage and round it off to 2 decimal places
        # product["percentage_discount"] = round(product["percentage_discount"], 2)
        product_obj = await Product.create(**product, business=user) 
        product_obj = await product_pydantic.from_tortoise_orm(product_obj) 
        return {
            "status": "ok",
            "data": product_obj
        }
    else:
        product["percentage_discount"] = 0.0
        return {
            "status": "error",
            "detail": "Original price cannot be zero"
        }


@app.get("/product")
async def get_products():
    products = await product_pydantic.from_queryset(Product.all())
    return {"status": "ok", "data": products}


@app.get("/product/{id}")
async def get_product(id: int): 
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    response = await product_pydantic.from_queryset_single(Product.get(id=id))

    return {
        "status": "ok", 
        "data": {
            "product_details": response,
            "business_details": {
                "name": business.business_name,
                "city": business.city,
                "region": business.region,
                "description": business.business_description,
                "logo": business.logo,
                "owner_id": owner.id,
                "email": owner.email,
                "join_date": owner.join_date.strftime("%b %d %Y")
            },
        }
        }
    
@app.delete("/product/{id}")
async def delete_product(id: int, user: user_pydantic = Depends(get_current_user)): # type: ignore
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    if owner == user:
        await product.delete()
        return {
                "status": "ok", 
                "detail": "Product deleted successfully"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

@app.put("/products/{id}")
async def update_product(
    id: int,
    update_info: product_pydanticIn, # type: ignore
    user: user_pydantic = Depends(get_current_user) # type: ignore
    ):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    
    update_info = update_info.dict(exclude_unset=True)
    update_info["date_published"] = datetime.now()
    
    if user == owner and update_info["original_price"] > 0:
        
        update_info["percentage_discount"] = ((update_info["original_price"] - update_info["new_price"]) / update_info["original_price"]) * 100
        product_obj = await product.update_from_dict(update_info)
        product_obj.save()
        response = await product_pydantic.from_tortoise_orm(product_obj)
        return {
            "status": "ok",
            "data": response
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Not found or original price cannot be zero or you are not the owner",
            headers={"WWW-Authenticate": "Bearer"}
        )


@app.put("/business/{id}")
async def update_business(
    id: int, 
    update_info: business_pydanticIn, # type: ignore
    user: user_pydantic = Depends(get_current_user)# type: ignore
    ): 
    update_info = update_info.dict(exclude_unset=True)
    business = await Business.get(id=id)
    owner = await business.owner
    if owner == user:
        business_obj = await business.update_from_dict(update_info)
        business_obj.save()
        response = await business_pydantic.from_tortoise_orm(business_obj)
        return {
            "status": "ok",
            "data": response
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Not found or you are not the owner",
            headers={"WWW-Authenticate": "Bearer"}
        )



register_tortoise(
    app,
    db_url= "sqlite://database.sqlite3",
    modules={'models': ['models']},
    generate_schemas=True,
    add_exception_handlers=True
)




