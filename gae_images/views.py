import logging

from django.http import HttpResponse

def show(request, obj_id, obj_class, img_call):

    obj = obj_class.objects.get(id=int(obj_id)) 

    exec("image_data = obj.%s" % img_call)

    return HttpResponse(image_data, content_type="image/png")
