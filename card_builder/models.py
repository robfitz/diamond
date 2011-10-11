import logging, sys
import urllib
import png

from django.db import models
from django.contrib import admin
from google.appengine.api import images

from djangotoolbox.fields import BlobField

def icon_text(icon_name, text):
    url = "https://chart.googleapis.com/chart?chst=d_simple_text_icon_left&chld=%s|16|000000|%s|16|000000|000000" % (text.replace("", "%20"), icon_name)
    image = urllib.urlopen(url)
    file = image.read()
    return file 

# returns image data from text
def text(message, font_size=12, is_bold=True):
    toks = message.split(' ')
    wrapped_message = ""
    line_length = 0
    for tok in toks:
        if not wrapped_message:
            wrapped_message = tok
            line_length = len(tok)
        elif line_length + len(tok) < 42:
            wrapped_message = "%20".join([wrapped_message, tok])
            line_length += len(tok) + 1
        else:
            wrapped_message = "|".join([wrapped_message, tok])
            line_length = len(tok)

    if is_bold:
        bold = "b"
    else:
        bold = "_"

    url = "https://chart.googleapis.com/chart?chst=d_text_outline&chld=000000|%s|l|ffffff|%s|%s" % (font_size, bold, wrapped_message)

    image = urllib.urlopen(url)
    file = image.read()
    return file 


class CardImage(models.Model):

    rendered = BlobField()


    def image(self, force_refresh=False):

        if not self.rendered or force_refresh:
            self.render_image(self.card)

        return self.rendered

    
    def render_image(self, card):

        layers = []

        # card border w/ rounded corners is done in
        # css, so we skip that

        # layer appropriate background/border color
        layers.append( ( KeywordImage.objects.get(keyword=card.caste).image_data, 0, 0, 1.0, images.TOP_LEFT ) )

        ability_y = 312

        #name
        layers.append( ( text(card.name, 14, True), 35, 35, 1.0, images.TOP_LEFT ) )

        # cost
        layers.append( ( text(str(card.tech_level), 14, True), 303, 35, 1.0, images.TOP_LEFT ) )

        #card image 
        if card.image_data():
            img = images.Image(card.image_data())
            img.resize(width=294, height=243)
            img = img.execute_transforms(output_encoding=images.PNG)
            layers.append( ( img, 27, 57, 1.0, images.TOP_LEFT ) )

        # add the card's ability text
        if card.defense:
            # creature. add attack & defense.  
            img = keyword('defense', str(card.defense))
            layers.append( ( img, 32, ability_y, 1.0, images.TOP_LEFT ) ) 

            ability_y += images.Image(img).height

            img = keyword(card.attack_type, str(card.attack))
            layers.append( ( img, 32, ability_y, 1.0, images.TOP_LEFT ) ) 
            ability_y += images.Image(img).height

        if card.direct_damage:
            img = keyword('direct_damage', str(card.direct_damage))
            layers.append( ( img, 32, ability_y, 1.0, images.TOP_LEFT ) ) 
            ability_y += images.Image(img).height

        if card.resource_bonus:
            img = keyword('resources', str(card.resource_bonus))
            layers.append( ( img, 32, ability_y, 1.0, images.TOP_LEFT ) ) 
            ability_y += images.Image(img).height

        if card.tech_change:
            img = keyword('tech', str(card.tech_change))
            layers.append( ( img, 32, ability_y, 1.0, images.TOP_LEFT ) ) 
            ability_y += images.Image(img).height

        if card.draw_num:
            img = keyword('draw', str(card.draw_num))
            layers.append( ( img, 32, ability_y, 1.0, images.TOP_LEFT ) ) 
            ability_y += images.Image(img).height 


        rendered = smart_composite(layers, 350, 489, output_encoding=images.JPEG) 
        self.rendered = rendered 
        self.save()


# if the composite fails due to bad or missing images,
# smart_composite will try to make it work by removing
# bad layers
def smart_composite(layers, w, h, output_encoding):
    
    good_layers = []
    for layer in layers:
        try:
            # this transform is meant to be thrown away. 
            # it's just being used to find out if GAE 
            # images API will accept the image data.
            img = images.Image(layer[0])
            img.resize(width=500, height=500)
            img = img.execute_transforms()

            good_layers.append(layer)
        except:
            # bad layer
            pass

    if len(layers) > 0:
        return images.composite(good_layers, w, h, output_encoding=output_encoding) 
    else:
        return None


def keyword(keyword, message=""):

    layers = []

    # get icon & number

    keyword_image = KeywordImage.objects.get(keyword=keyword)
    if keyword_image.google_icon_name: 
        layers.append( ( icon_text(keyword_image.google_icon_name, message), 0, 0, 1.0, images.TOP_LEFT) )
    elif keyword_image.image_data:
        # separately compile the icon & number
        layers.append( ( keyword_image.image_data, 0, 0, 1.0, images.TOP_LEFT) )
        layers.append( ( icon_text("", message), 0, 0, 1.0, images.TOP_LEFT) )

    # add full description text
    if keyword_image.help_text:
        layers.append( ( text(keyword_image.help_text), 50, 0, 1.0, images.TOP_LEFT) )

    rendered = smart_composite(layers, 290, 40, output_encoding=images.PNG) 

    return rendered


class KeywordImage(models.Model):

    keyword = models.CharField(max_length=50)

    google_icon_name = models.CharField(max_length=50, blank=True, default="", help_text="Icon names from here: http://code.google.com/apis/chart/image/docs/gallery/dynamic_icons.html#icon_list")

    help_text = models.TextField(default="", blank=True, help_text="In the case of card abilities (e.g. flying), this help text is printed on the card along w/ the ability icon, which is held in image_data")

    image_data = BlobField(blank=True, null=True)


class KeywordImageAdmin(admin.ModelAdmin):

    list_display_links = ('__unicode__',)
    list_display = ('__unicode__', 'keyword', 'google_icon_name', 'help_text')
    list_editable = ('keyword', 'google_icon_name', 'help_text')

    def __unicode__(self):
        return self.keyword

admin.site.register(KeywordImage, KeywordImageAdmin)
admin.site.register(CardImage)


