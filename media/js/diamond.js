function get_unit_body(model, alignment) {
    var model_fields = model.fields;
    var unit_piece = $("<div title='" + model_fields.tooltip + "' class='attack_" + model_fields.attack + "' id='" + model.pk + "'></div>");

    var url = "";
    if (alignment == 'friendly' && model_fields.icon_url_back) {
        url = model_fields.icon_url_back;
    } 
    else {
        url = model_fields.icon_url;
    }
    $("<img src='" + url + "' />").appendTo(unit_piece).load(function() {
        var x_off = (60 - $(this).width()) / 2;
        $(this).css("left", x_off); 
    }); 

    // container for holding attack icons
    var unit_attack = $("<div class='unit_attack'></div>").appendTo(unit_piece);

    // attack icons, one per attack point
    for (var i = 0; i < model_fields.attack; i ++) {
        $("<img src='/media/units/attack_type_" + model_fields.attack_type + ".png' />").appendTo(unit_attack);
    }

    //life bubbles, one per defense, which display life & damage
    var def = $("<div class='defense'></div>").appendTo(unit_piece); 
    for (i = 0; i < model_fields.defense; i ++) {
        $("<div class='defense_point health'></div>").appendTo(def); 
    }

    $("<div class='card_name'>T" + model.fields.tech_level + ":" + model.fields.name + "</div>").appendTo(unit_piece);

    return unit_piece;
}
