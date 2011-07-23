function show_number(target, amount) {
    if (amount < 0) {
        show_message(target, amount, "red");
    }
    else  {
        show_message(target, "+" + amount, "green");
    }
}


function show_message(target, message, color) {
    var x = $("<h1 class='feedback'></h1>").appendTo(target);
    x.addClass(color);
    x.text(message); 

    x.animate({ top:"-=40" },
        { duration: 1000 });
        x.fadeOut(1000, function() {
            $(this).remove();    
        });
}

function Board() { 

    // board.friendly[node_id] == { type: unit, unit: Unit }
    this.friendly = {};
    this.ai = {}; 

    this.on_unit_placed;

    this.to_json = function() {

        var json = [];
        for (key in this.friendly) {
            if (this.friendly[key] && this.friendly[key].type == "unit") {
                json.push( this.friendly[key].to_json() );
            }
        }
        for (key in this.ai) {
            if (this.ai[key] && this.ai[key].type == "unit") {
                json.push( this.ai[key].to_json() );
            }
        }
        return json; 
    }

    this.cancel_cast = function() {
        $(".card").removeClass("selected");

        //clear old targetting events 
        $(".node").removeClass("targettable").unbind("click");

        $("#friendly_tech").removeClass("targettable").unbind("click");
    }

    this.begin_cast = function(card_json, jq_valid_targets) {

        this.cancel_cast();

        // highlight valid targets and allow them to respond to click
        
        var board = this;

        jq_valid_targets.addClass("targettable").click( function (event) {
                var node = $(event.currentTarget);
                var node_id = node.attr("name");

                var node_alignment = node.parent().hasClass("friendly") ? node_alignment = "friendly" : node_alignment = "ai"; 

                board.place_unit(card_json, node_id, node_alignment);
        });

        jq_valid_targets.droppable( {
            drop: function(event, ui) {

                var node = $(event.target);
                var node_id = node.attr("name");

                var node_alignment;
                if (node.parent().hasClass("friendly")) {
                    node_alignment = "friendly";
                }
                else node_alignment = "ai";

                board.place_unit(card_json, node_id, node_alignment);
            },
            over: function(event, ui) {
                $(event.target).addClass("hovered");   
            },
            out: function(event, ui) {
                $(event.target).removeClass("hovered");
            },
        }); 
    }

    this.place_unit = function(card_json, node_id, node_alignment) {
        var unit = new Unit(card_json, node_id, node_alignment);

        this[node_alignment][node_id] = unit; 

        this.cancel_cast();

        if (this.on_unit_placed) {
            var event = { 'data': { 'unit': unit, 'node_id': node_id, 'node_alignment': node_alignment } };
            this.on_unit_placed(event);
        }
    } 
}

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

function Match() {

    // "ai", "pvp", "puzzle"
    this.type = "ai";

    this.winner = null;

    this.tech = { 
        'friendly': 1, 
        'ai': 1 
    };
    this.life = { 
        'friendly': 10, 
        'ai': 10 
    };
    this.phase = -1;
    this.turn_num = 1;

    this.hand_cards = {};

    //same format as hand_cards, but contains
    //every card played so far this game as a
    //lookup for what's already happened
    this.played_cards = {};
    
    //the data returned from the server after ending
    //a turn, including what the ai opponent does and
    //which cards you draw
    this.turn_data = null;
}; 


function Unit(json_model, location_node_pk, alignment) { 

    // full details of this unit just in case
    this.model = json_model;
    this.model_fields = this.model.fields;

    this.alignment = alignment;

    // move some common fields out of the json and
    // to make them more easily accessible
    this.remaining_life = this.model_fields.defense;
    this.total_life = this.model_fields.defense;
    this.attack = this.model_fields.attack; 

    this.must_be_killed = false;

    this.type = "unit"; 

    // for differentiating between model state and animation state
    this.gui_life = this.remaining_life;
    this.undisplayed_damage_queue = [];

    this.rubble_duration = 1;

    //init and add to board
    this.node = $(".board." + alignment + " .node[name='" + location_node_pk + "']");
    this.node.addClass("unit");
    this.node.addClass("occupied"); 
    this.node.removeClass("empty"); 
    this.node.attr("id", this.model.pk);

    this.node.children(".unit_piece").remove();
    
    var unit_piece = get_unit_body(this.model, this.alignment).appendTo(this.node);
    unit_piece.addClass("unit_piece");

    init_tooltips(".node");

    var w = parseInt(unit_piece.css('width'));
    var h = parseInt(unit_piece.css('height'));

    var node_w = parseInt(this.node.css('width'));
    var node_h = parseInt(this.node.css('height'));

    unit_piece.css('width', 0);
    unit_piece.css('height', 0);
    unit_piece.css('left', node_w/2 + "px");
    unit_piece.css('top', node_h/2 + "px");
    unit_piece.animate( 
            { 
                width: w, 
                height: h,
                left: "-=" + w / 2,
                top: "-=" + h / 2,
            },
            {
                duration: 400,
            });

    show_message(this.node, this.model_fields.name);


    this.to_json = function() {
        return { "id": this.model.pk,
            "node_id": this.node.attr("name"),
            "alignment": this.alignment } 
    }

    this.damage = function() {
        return this.total_life - this.remaining_life;
    }

    this.heal = function() { 
        if (this.total_life - this.remaining_life != 0) {
            show_number(this.node, this.total_life - this.remaining_life);
        }
        this.remaining_life = this.total_life;
    }

    this.suffer_damage = function(delta_damage, damage_source) { 

        if (damage_source && damage_source.type == "unit" && this.model_fields.attack_type == "counterattack") {
            // counter-attack if appropriate
            damage_source.suffer_damage(this.attack, this); 
        }

        this.remaining_life -= delta_damage;

        this.undisplayed_damage_queue.push(delta_damage);

        if (this.remaining_life <= 0) {
            this.die();
        } 
    } 

    this.show_next_damage = function() {

        var delta_damage = this.undisplayed_damage_queue.shift();

        if (delta_damage) {

            for (var i = 0; i < delta_damage; i ++) {
                this.node.find(".defense_point.health").filter(":last").removeClass("health").addClass("damage");
            }

            this.gui_life -= delta_damage;

            var unit = this;
            this.node.children(".unit_piece").effect("bounce", "fast", function() {
                    if (unit.gui_life <= 0) {
                        // die if it's relevant

                        if (unit.rubble_duration > 0) {
                            unit.node.children(".unit_piece").hide("explode", function() {

                                    // remove unit icon
                                    $(this).remove();

                                    // create rubble icon
                                    var rubble = $("<div title='Rubble appears when units die and prevents new units from being placed until it decays.' class='rubble r_" + unit.rubble_duration + "'></div>").appendTo(unit.node);
                                    $("<img src='/media/units/rubble.png' />").appendTo(rubble); 

                                    init_tooltips(".node");

                                    // intro animation
                                    rubble.hide();
                                    rubble.show("bounce");
                            }); 
                        }
                        else {
                            unit.node.children(".unit_piece").hide("explode", function() {

                                    // remove unit icon
                                    $(this).remove();
                            });
                        } 

                    } 
            });
            show_number(this.node, -1 * delta_damage); 
        } 
    }

    this.die = function() { 

        this.node.addClass("empty");
        this.node.removeClass("unit"); 
        this.node.removeClass("occupied");

        if (this.rubble_duration > 0) {
            // killed. leave in place but become rubble
            this.type = "rubble";

            this.node.addClass("occupied");
            this.node.removeClass("empty"); 

            boards[alignment][this.node.attr('name')] = { 
                    "type": "rubble",
                    "amount": this.rubble_duration,
                };
        } 
        else {
            this.type == "dead";

            // killed and no rubble left. remove from board.
            boards[this.alignment][this.node.attr('name')] = null;
        }

    }
}
