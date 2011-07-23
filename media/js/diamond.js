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

function Match(game_type, game_goal) {

    // set to true when ready
    this.is_init = false;

    // "ai", "pvp", "puzzle"
    this.type = game_type;

    // "kill units" or "kill player"
    this.goal = game_goal;

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

    this.node.mouseenter( function ( e ) {

        $(".attacking_from, .attacking_to").hide();

        var node = $(e.currentTarget);
        var node_alignment = node.parent().hasClass("friendly") ? "friendly" : "ai"; 

        var unit = boards[node_alignment][node.attr("name")];

        var path = unit.get_attack_path(board_node_pks, board_node_locs, false);
        for (i = 0; i < path.length; i ++) { 
            var node = path[i];
            var dir = (node.alignment == unit.alignment ? "attacking_from" : "attacking_to");

            //if (node.action == "skip") continue;
            if (node.action == "damage_unit") {
                $("." + node.alignment + " .r" + node.row + ".x" + node.x + " .unit_piece").addClass("hostile_targetting"); 
            }
            else { 
                $("." + node.alignment + " .r" + node.row + ".x" + node.x + " ." + dir).show(); 
            }
        } 
    });

    this.node.mouseleave(function ( e ) {
        $(".attacking_from, .attacking_to").hide();
        $(".unit_piece").removeClass("hostile_targetting");
    });


    this.to_json = function() {
        return { "id": this.model.pk,
            "node_id": this.node.attr("name"),
            "alignment": this.alignment } 
    }

    this.get_attack_path = function(board_node_pks, board_node_locs, deal_damage) {

        if (this.model_fields.attack_type == "na"
            || this.model_fields.attack_type == "wall"
            || this.model_fields.attack_type == "counterattack") {

            // no attack from this unit 
            return [];
        }


        var path_info = [ ];

        var alignment = this.alignment;
        var starting_alignment = this.alignment;
        var opponent_alignment = (starting_alignment == "friendly" ? "ai" : "friendly"); 

        var node_id = this.node.attr("name");
        var row = board_node_locs[node_id].row;
        var x = board_node_locs[node_id].x;

        var is_searching = true; 
        var d_row = 1;
        var steps_taken = 0; 

        //if (this.model_fields.attack_type == "melee") {
            // units which start attacking from
            // exactly where they're standing without
            // passing over any nodes get an extra starting
            // point for display purposes
            path_info.push({ 
                node_id: next_node_id,
                'x': x,
                'row': row,
                'alignment': alignment,
                'drow': "+=0",
                'drow_reverse': '+=0',
                'dx': "+=0",
                'dx_reverse': "+=0" 
            });
        //}

        while (is_searching) {

            if (alignment != starting_alignment) {
                //we've entered ai territory
                d_row = -1;
            }
            else if (row == 2) {
                //breaching ai territory, from front row to front row
                d_row = 0;
                alignment = (alignment == "friendly" ? "ai" : "friendly"); 
            }
            else {
                //moving forward from your back[er] row
                d_row = 1;
            }

            //check [row-1][x]
            row = row + d_row;
            var old_x = x;

            if (Math.abs(x) > row) {
                // keep movement inside the triangle.
                // this is a lazy hack to avoid making a
                // proper tree structure for this board.
                // specifically, this maintains the sign of
                // x while capping it at [row], so r=1, x=-2
                // becomes r=1, x=-1
                x = row * x / Math.abs(x);
            }

            //okay, we have our next node!
            var next_node_id = board_node_pks[row][x];

            var path_node = { 
                node_id: next_node_id,
                'x': x,
                'row': row,
                'alignment': alignment 
            };

            if (starting_alignment == "ai") {
                path_node.drow = "+=100";
                path_node.drow_reverse = "-=100";
            }
            else {
                path_node.drow = "-=100";
                path_node.drow_reverse = "+=100";
            }

            if (old_x < x) {
                path_node.dx = "+=100";
                path_node.dx_reverse = "-=100";
            }
            else if (old_x > x) {
                path_node.dx = "-=100";
                path_node.dx_reverse = "+=100";
            }
            else { 
                path_node.dx = "+=0";
                path_node.dx_reverse = "+=0";
            }

            path_info.push(path_node);

            steps_taken ++;
            if (this.model_fields.attack_type == "flying" && steps_taken < 3) {
                // flying units always pass over the subsequent 2 nodes
                if (steps_taken < 2) {
                    path_node.action = "skip";
                }
                continue;
            }
            if (alignment == starting_alignment && this.model_fields.attack_type == "ranged") {
                // ranged units always pass over friendlies

                if (row < 2) {
                    path_node.action = "skip";
                }
                continue;
            }

            //is there a guy there?
            var collision_unit = get_unit_at(alignment, next_node_id)
            if (collision_unit && collision_unit.type == "unit") {
                if (alignment == starting_alignment) { 

                    // we've already handled flying & ranged,
                    // so i am melee -- done :*(
                    path_node.action = "blocked";
                    is_searching = false;
                }
                else {
                    //no? ai! hit it!
                    path_node.action = "damage_unit";
                    path_node.damaged_unit = collision_unit;

                    is_searching = false;
                    if (deal_damage) {
                        damage_unit(next_node_id, alignment, this.attack, this); 
                    }
                }
            }
            else if (alignment == opponent_alignment && row <= 0) {
                //is it 0,0? hit the player!
                is_searching = false; 

                attack = this.attack;
                path_node.action = "damage_player";
            }
            else {
                //not the player and no unit there. loop
            } 
        } 
        return path_info;

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
