function surrender() { 
    if (match.phase == 1) {
        $("input[name='card1']").val('surrender');
        $("input[name='node1']").val('surrender'); 
        $("input[name='align1']").val('surrender'); 

        // jump to 0 life
        damage_player("friendly", match.life['friendly']);
    }
    else if (match.phase == 3) {
        $("input[name='card2']").val('surrender');
        $("input[name='node2']").val('surrender'); 
        $("input[name='align2']").val('surrender'); 

        // jump to 0 life
        damage_player("friendly", match.life['friendly']);
    }
}

function pass_turn() {
    if (match.phase == 1) {
        $("input[name='card1']").val('pass');
        $("input[name='node1']").val('pass'); 
        $("input[name='align1']").val('pass'); 

        next_phase(); 
    }
    else if (match.phase == 3) {
        $("input[name='card2']").val('pass');
        $("input[name='node2']").val('pass'); 
        $("input[name='align2']").val('pass'); 

        next_phase();
    }
}

var match = {

    // "ai", "pvp", "puzzle"
    type: "ai",

    winner: null,

    tech: { 
        'friendly': 1, 
        'ai': 1 
    },
    life: { 
        'friendly': 10, 
        'ai': 10 
    },
    phase: -1,

    hand_cards: {},

    //same format as hand_cards, but contains
    //every card played so far this game as a
    //lookup for what's already happened
    played_cards: {},
    
    //the data returned from the server after ending
    //a turn, including what the ai opponent does and
    //which cards you draw
    turn_data: null,
};

    var UNIT_R = 25;

    var phases = ["draw", "play_1", "attack", "play_2", "ai_draw", "ai_play_1", "ai_attack", "ai_play_2"];

    var MAX_TECH = 5; 

    var boards = {};
    var board_node_locs = {};
    var board_node_pks = {};

    $(function() {
        boards.friendly = {};
        boards.ai = {}; 
    });

    function draw_starting_hand() { 
        $.ajax({ url: "/playing/first_turn/",
                success: function(data) {
                    match.turn_data = eval('(' + data + ')');
                    next_phase(true);
                }
            }); 
    }

    function end_turn() {
        $.post("/playing/end_turn/",
            $("#current_turn").serialize(),
            function(data) {

                if (match.winner) {
                    // if the match has already been won or
                    // lost, ignore how the AI responds
                    return;
                }

                match.turn_data = eval('(' + data + ')');

                verify_board_state(match["turn_data"]["verify_board_state_before_ai"]);

                // TODO: this probably shouldn't be here. clean up
                // the end of my turn/beginning of their turn ordering
                heal_units("ai");
                next_phase();
            }
        );

        $("input[name='card1']").val("");
        $("input[name='node1']").val("");
        $("input[name='align1']").val("");
        $("input[name='card2']").val("");
        $("input[name='node2']").val("");
        $("input[name='align2']").val("");
    }

    function verify_board_state(server_board) {


        if (server_board["life"]["friendly"] != match["life"]["friendly"]) {
            alert("different life totals, friendly (server v local): " + server_board['life']['friendly'] + "," + match['life']['friendly']);
        } 
        if (server_board["life"]["ai"] != match["life"]["ai"]) {
            alert("different life totals, ai (server v local): " + server_board['life']['ai'] + "," + match['life']['ai']);
        }


        if (server_board["tech"]["friendly"] != match["tech"]["friendly"]) {
            alert("different tech totals, friendly (server v local): " + server_board['tech']['friendly'] + "," + match['tech']['friendly']);
        } 
        if (server_board["tech"]["ai"] != match["tech"]["ai"]) {
            alert("different tech totals, ai (server v local): " + server_board['tech']['ai'] + "," + match['tech']['ai']);
        }

        verify_board_state_for(server_board, "ai");
        verify_board_state_for(server_board, "friendly");
    }
    function verify_board_state_for(server_board, align) {

        var board = server_board['boards'][align];
        for (node_key in board) { 
            
            var s_node = board[node_key];
            var node = boards[align]["" + s_node.node];

            if (!s_node && !node) {
                //both are null, that's okay
            }
            else if ((!s_node || s_node["type"] == "empty") && (!node || node['type'] == "empty")) {
                //both are null (or empty), that's okay
            } 
            else if (!s_node || !node) {
                alert("either server,local node is null: " + s_node + "," + node + ". stype=" + s_node["type"] + " at key: " + node_key + "," + align);
            }
            else if (s_node['type'] != node['type']) {
                alert("board states don't match, different types on node=" + node_key + " " + align + ". server expected " + s_node.type);

            }
            else {

                // types match, check contents 

                if (node.type == "empty") {
                    // pass
                }
                else if (node.type == "unit") {
                    // same card PK?
                    if (node.model.pk != s_node.card) {
                        alert("server (" + s_node.card + ") and local (" + node.model.pk + ") unit card PKs don't match");

                    }
                    
                    // same damage?
                    if (s_node.damage != node.damage()) {
                        alert("server (" + s_node.damage + ") and local (" + node.damage() + ") unit damages don't match on " + node_key + "," + align);
                    }
                }
                else if (node.type == "rubble") {
                    // same rubble amount?
                    if (s_node.amount != node.amount) {
                        alert("server (" + s_node.amount + ") and local (" + node.amount + ") rubble amounts don't match on " + node_key + "," + align);
                    } 
                }
            } 
        }
    }

    function next_phase(is_first_turn) {

        if (match.winner) return;

        if (is_first_turn) {
            var units = match.turn_data.ai_starting_units;
            if (units) {

                // TODO: this shouldn't be determined like this,
                //       but it'll work for now.
                match.type = "puzzle"; 
                $(".life.ai h1").text("∞"); 

                for (i = 0; i < units.length; i ++) {
                    var card = match.turn_data.ai_cards[i];
                    var node = $(".board.ai [name='" + units[i].node + "']");
                    ai_cast(card,
                            node,
                            'ai',
                            is_first_turn); 
                    boards['ai'][units[i].node].must_be_killed = units[i].must_be_killed; 
                } 
            }
        }

        match.phase ++;
        cancel_cast();

        if (match.phase >= phases.length) {
            match.phase = 0;
            
        }

        $("#phases").find("li.active").removeClass("active");
        $("#phases").find("#" + match.phase).addClass("active");

        if (match.phase == 0 ) {
            if (match.turn_data) {
                //draw cards
                var i = 0;
                while (i < match.turn_data.player_draw.length) {
                    setTimeout ( function() {
                        var card = match.turn_data.player_draw.pop();
                        add_card_to_hand( card );
                    }, 200 * (i+1));
                    i ++; 
                }
                setTimeout ( function() {
                    heal_units("friendly");
                    next_phase();
                }, 200 * i); 
            }
            else {
                next_phase();
            }
        }
        else if (match.phase == 1) {
            if ($("#friendly_hand").children().length == 0) {
                setTimeout(next_phase, 400); 
            }
            else {
                //do nothing.
                //wait for player to play card
            }
        }
        else if (match.phase == 2) {
            //begin logic for auto-attacking
            var delay = do_attack_phase("friendly");
            setTimeout(next_phase, delay);
        }
        else if (match.phase == 3) {
            if ($("#friendly_hand").children().length == 0) {
                setTimeout(next_phase, 400); 
            }
            else {
                //do nothing.
                //wait for player to play card
            }
        }
        else if (match.phase == 4) {
            //ai draw & heal
            remove_one_rubble("friendly"); 
            end_turn();

        }
        else if (match.phase == 5 ) {
            do_ai_play_1();
            setTimeout ( function() {
                next_phase();
            }, 1000); 
        } 
        else if (match.phase == 6) {
            //ai attack
            var delay = do_attack_phase("ai");
            setTimeout(next_phase, delay + 1000);
        }
        else if (match.phase == 7 ) {
            do_ai_play_2();
            remove_one_rubble("ai");

            verify_board_state(match.turn_data["verify_board_state_after_ai"]);

            setTimeout ( function() {
                next_phase();
            }, 1000); 

        }
    }

    function do_ai_play_1() { 
        if (match.turn_data.ai_turn[0]) {
            //ai play 1
            if (match.turn_data.ai_turn[0].fields.is_tech_1) {
                ai_tech_up(1); 
            }
            else if (match.turn_data.ai_cards[0]) {
                var target = match.turn_data.ai_turn[0].fields.target_node_1;
                var align = match.turn_data.ai_turn[0].fields.target_alignment_1; 
                //ai summons
                var node = $(".board." + align + " .node[name='" + target + "']");
                ai_cast(match.turn_data.ai_cards[0], node, align);
            }
            else {
                //nothing to cast or tech up
            }
        }
    }

    function do_ai_play_2() {
        if (match.turn_data.ai_turn[0]) {
            //ai play 2
            if (match.turn_data.ai_turn[0].fields.is_tech_2) {
                ai_tech_up(1); 
            }
            else if (match.turn_data.ai_cards[1]) {
                var target = match.turn_data.ai_turn[0].fields.target_node_2;
                var align = match.turn_data.ai_turn[0].fields.target_alignment_2; 
                var node = $(".board." + align + " .node[name='" + target + "']");
                ai_cast(match.turn_data.ai_cards[1], node, align);
            }
            else {
                //nothing to cast or tech up
            }
        }
    } 

    /** returns the number of milliseconds this attack phase will require to animate */
    function do_attack_phase(alignment) { 
        var i = 0;
        var animation_ms = 0;
        $(".board." + alignment + " .node.unit .unit_piece").each( 
            function () { 
                var approach_dir = (alignment == "friendly" ? "-":"+");
                var retreat_dir = (alignment == "friendly" ? "+":"-");

                var to_animate = $(this);

                //find target
                var node_id = to_animate.parent().attr("name");

                var unit = boards[alignment][node_id];

                var attack_path = do_attack(unit, node_id, alignment);

                var opponent_alignment = (alignment == "friendly" ? "ai" : "friendly"); 

                var str = "";
                var current_animation_step = 0;
                for (var i = 0; i < attack_path.length; i ++) {
                    str += attack_path[i].drow + "," + attack_path[i].dx + "   "; 

                    if (i == 0) {
                        $(this).animate( { top: "+=0" }, { 
                            queue: true, 
                            duration: animation_ms,
                        });
                    }

                    animation_ms += 200;
                    $(this).animate(
                        {   top: attack_path[i].drow,
                            left: attack_path[i].dx,
                            "z-index": 2,
                        },
                        {
                            queue: true,
                            duration: 200,
                            complete: function() {
                                // what Im doing and to who
                                var action = attack_path[current_animation_step].action;
                                var target_node_pk = attack_path[current_animation_step].node_id;

                                //perform whatever action is relevant for this
                                //path step
                                if (action == "damage_player") {
                                    damage_player(opponent_alignment, unit.attack);
                                }
                                else if (action == "damage_unit") {
                                    damage_unit(target_node_pk, opponent_alignment, unit.attack, unit); 
                                } 

                                current_animation_step ++;

                            },
                        }
                    );
                }
                for (i = attack_path.length - 1; i >= 0; i --) {
                    animation_ms += 200;
                    $(this).animate(
                        {   top: attack_path[i].drow_reverse,
                            left: attack_path[i].dx_reverse,
                            "z-index": 2,
                        },
                        {
                            queue: true,
                            duration:200,
                            complete: function() { $(this).css("z-index", 1); }
                        }     
                    ); 
                }
                animation_ms += 500;
        });
        return animation_ms;
    }

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

    //init and add to board
    this.node = $(".board." + alignment + " .node[name='" + location_node_pk + "']");
    this.node.addClass("unit");
    this.node.addClass("occupied"); 
    this.node.removeClass("empty"); 
    this.node.attr("id", this.model.pk);

    this.node.children(".unit_piece").remove();
    
    var unit_piece = $("<div title='" + this.model_fields.tooltip + "' class='unit_piece attack_" + this.model_fields.attack + "' id='" + this.model.pk + "'></div>").appendTo(this.node);

    init_tooltips(".node");

    if (this.alignment == 'friendly' && this.model_fields.icon_url_back) {
        $("<img src='" + this.model_fields.icon_url_back + "' />").appendTo(unit_piece); 
    } 
    else {
        $("<img src='" + this.model_fields.icon_url + "' />").appendTo(unit_piece); 
    }



    // container for holding attack icons
    var unit_attack = $("<div class='unit_attack'></div>").appendTo(unit_piece);

    // attack icons, one per attack point
    for (var i = 0; i < this.model_fields.attack; i ++) {
        $("<img src='/media/units/attack_type_" + this.model_fields.attack_type + ".png' />").appendTo(unit_attack);
    }

    //life bubbles, one per defense, which display life & damage
    var def = $("<div class='defense'></div>").appendTo(unit_piece); 
    for (i = 0; i < this.total_life; i ++) {
        $("<div class='defense_point health'></div>").appendTo(def); 
    }

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

        if (damage_source.type == "unit" && this.model_fields.attack_type == "counterattack") {
            // counter-attack if appropriate
            damage_source.suffer_damage(this.attack, this); 
        }

        this.remaining_life -= delta_damage;
        show_number(this.node, -1 * delta_damage);

        for (var i = 0; i < delta_damage; i ++) {
            this.node.find(".defense_point.health").filter(":last").removeClass("health").addClass("damage");
        }

        var unit = this;
        this.node.children(".unit_piece").effect("bounce", "fast", function() { 
            if (unit.remaining_life <= 0) {
                unit.die();
            }
        });

    } 

    this.die = function() { 
        //killed. remove from board.
        boards[this.alignment][this.node.attr('name')] = null;


        this.node.addClass("empty");
        this.node.removeClass("unit"); 
        this.node.removeClass("occupied");

        var rubble = add_rubble(this.alignment, this.node, 1);
        rubble.hide();

        //this.node.children(".unit_piece").remove(); 
        this.node.children(".unit_piece").hide("explode", function() {
                $(this).remove();
                rubble.show("bounce");
            });

        if (this.alignment == 'ai' && match.type == 'puzzle') {
            for (var node_pk in boards['ai']) { 
                var unit = boards['ai'][node_pk]; 
                if (unit && unit['type'] == 'unit' && unit.must_be_killed) {
                    return;
                }
            }
            // all required units are dead, player won puzzle
            win();
        }
    }
}

function win() { 

    if (!match.winner) {
        setTimeout(function() { 
            $("#win_screen").show("slide", "slow"); 
            end_turn();
            match.winner = 'friendly';
            }, 500);
    }
}
function lose() {
    if (!match.winner) {
        setTimeout(function() {
            $("#lose_screen").show("slide", "slow");
            match.winner = 'ai';
            }, 500);
    }
}

function damage_unit(node_pk, alignment, delta_damage, damage_source) {
    var unit = boards[alignment][node_pk]; 
    if (!unit) return; 
    unit.suffer_damage(delta_damage, damage_source);

}

function heal_units(alignment) {
    for (var node_pk in boards[alignment]) {
        var unit = boards[alignment][node_pk]; 
        if (unit && unit['type'] == 'unit') {
            unit.heal();
            unit.node.find(".defense_point.damage").removeClass("damage").addClass("health");
        }
    }
}

    function ai_cast(card, node, alignment, is_first_turn) { 
        cast_card('ai', alignment, card, node, is_first_turn); 

        action_indicator(node, "AI cast " + card.fields.name);
    }


    function remove_one_rubble(alignment) {
        $(".board." + alignment + " .rubble").each( function() {
            show_message($(this).parent(), "-1");

            $(this).hide("puff", function() {
                $(this).children("img").first().remove(); 

                if ( $(this).children("img").size() == 0) {

                    boards[alignment][$(this).parent().attr('name')] = null;

                    $(this).parent().removeClass("occupied");
                    $(this).parent().addClass("empty"); 

                    $(this).remove(); 
                } 
                else {
                    this.show();
                }
            });
        });
    }

    function add_rubble(alignment, node, quantity) { 
        var rubble = $("<div title='Rubble appears when units die and prevents new units from being placed until it decays.' class='rubble r_" + quantity + "'></div>").appendTo(node);

        init_tooltips(".node");

        for (var i = 0; i < quantity; i ++) {
            $("<img src='/media/units/rubble.png' />").appendTo(rubble); 
        } 
        node.addClass("occupied");
        node.removeClass("empty"); 

        boards[alignment][node.attr('name')] = { 
                "type": "rubble",
                "amount": quantity
            };
        return rubble;
    }

    function cast_card(caster_alignment, target_alignment, card, node, skip_side_effects) {

        if (card.fields.target_aiming == "all") {
            nodes = node.parent().children(".empty");
        }
        else if (card.fields.target_aiming == "chosen") {
            nodes = node;
        }
        else {
            alert('unknown card target aiming: ' + card.fields.target_aiming);
        }

        for (var i = 0; i < nodes.length; i ++) {
            node = nodes.eq(i);

            if (card.fields.direct_damage) {
                damage_unit(node.attr('name'), target_alignment, card.fields.direct_damage, card); 
            }
            if (card.fields.defense) { 

                var unit = new Unit(card, node.attr('name'), target_alignment);

                match.played_cards[card.pk] = card.fields; 
                boards[target_alignment][node.attr("name")] = unit; 
            }
            if (!skip_side_effects && card.fields.tech_change) {
                if (caster_alignment == "ai") {
                    ai_tech_up(card.fields.tech_change);
                }
                else {
                    tech_up(card.fields.tech_change);
                } 
            }
        } 
    }

    function get_unit_at(alignment, next_node_id) {
        return boards[alignment][next_node_id];
    }

    /** 
     * returns a list of node points in format: 
     * { dx:XXX, drow:XXX, [action:damage_unit/damage_player/blocked], node_id:node_pk } 
     */ 
    function do_attack(unit, node_id, alignment) {

        if (!unit) {
            alert('attempted attack from non-existant unit at node ' + node_id + " of alignment " + alignment);
            return []; 
        }

        if (unit.attack == 0
            || unit.model_fields.attack_type == "na"
            || unit.model_fields.attack_type == "wall"
            || unit.model_fields.attack_type == "counterattack") {

            // no attack from this unit 
            return [];
        }

        var starting_alignment = alignment;
        var opponent_alignment = (starting_alignment == "friendly" ? "ai" : "friendly"); 

        var row = board_node_locs[node_id].row;
        var x = board_node_locs[node_id].x;

        var is_searching = true;

        var d_row = 1;

        var path_info = [];

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
            var next_node_id = board_node_pks[row][x] 

            var path_node = { node_id: next_node_id };
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

            //is there a guy there?
            var collision_unit = get_unit_at(alignment, next_node_id)
            if (collision_unit && collision_unit.type == "unit") {
                if (alignment == starting_alignment) { 

                    //am i ranged? loop!
                    if (unit.model_fields.attack_type == "ranged") {
                        continue;
                    }
                    else {
                        //am i melee? done :*(
                        path_node.action = "blocked";
                        is_searching = false;
                    }
                }
                else {
                    //no? ai! hit it!
                    path_node.action = "damage_unit";
                    is_searching = false;
                }
            }
            else if (alignment == opponent_alignment && row <= 0) {
                //is it 0,0? hit the player!
                is_searching = false; 

                attack = unit.attack;
                path_node.action = "damage_player";
            }
            else {
                //not the player and no unit there. loop
            } 
        } 
        return path_info;
    }

    function set_player_life(alignment, amount) { 
        match.life[alignment] = amount;
        var str = "" + amount;
        if (amount < 10) str = " " + str;
        $(".life." + alignment + " h1").text(str);
    }

    function damage_player(alignment, amount) {

        if (match.type == "puzzle" && alignment == "ai") {
            // enemy is immortal in puzzle mode
            return;
        } 

        match.life[alignment] -= amount;

        var str = "" + match.life[alignment];
        if (amount < 10) str = " " + str;
        $(".life." + alignment + " h1").text(str);

        show_number($(".life." + alignment), -1 * amount);

        if (match.life[alignment] <= 0) {
            if (alignment == "ai") {
                win();
            }
            else {
                lose();
            } 
        }
    }

    function add_card_to_hand(card_json) {
        var card = $("<li class='card' id='" + card_json.pk + "'></li>").appendTo("#friendly_hand");

        var f = card_json.fields;
        card_str = "T" + f.tech_level + ": " + f.name;
        card.text(card_str);

        card.attr("title", f.tooltip);
        init_tooltips("#friendly_hand");

        match.hand_cards[card_json.pk] = card_json; 

        card.draggable({ 
            start: function(event, ui) { 
                begin_card_drag(event, card, card_json); 
            },
            revert: "invalid",
            //snap: ".node",
            //snapMode: "inner",
        });

        card.click( function(event) {
            begin_card_drag(event, card, card_json); 
        });
    }

    function begin_card_drag(event, ui, card_json) {
            cancel_cast();

            if (match.phase != 1 && match.phase != 3) {
                //not in an interactive phase, so no clicky
                return;
            }
            if (match["tech"]["friendly"] < card_json.fields.tech_level
                && match["tech"]["friendly"] >= MAX_TECH) {

                //we can neither play nor tech up with this
                //card, so don't allow it to be clicked
                return;
            }

            ui.addClass("selected");

            // if the tech level is high enough, select the places
            // on the board we can use this card
            if (match["tech"]["friendly"] >= card_json.fields.tech_level) {
                // find valid targets based on card targetting type
                // e.g. summoning is: friendly board > empty nodes

                var targets;
                var board_selector = ".board"; 
                var node_selector = ".node";

                if (card_json.fields.target_alignment != 'any') {
                    var align = (card_json.fields.target_alignment == "enemy" ? "ai" : "friendly");
                    board_selector += "." + align;
                }

                var occ = card_json.fields.target_occupant;
                if (occ == "unit" || occ == "occupied") {
                    node_selector += ".unit"; 
                }
                else if (occ == "empty") {
                    node_selector += ".empty";
                }

                targets = $(board_selector + " " + node_selector); 

                // highlight valid targets and allow them to respond to click
                targets.addClass("targettable").click( function (event) {
                    cast($(".card.selected"), $(event.currentTarget));
                });

                targets.droppable( {
                    drop: function(event, ui) {
                        cast($(".card.selected"), $("#" + event.currentTarget.id)); 
                    },
                    over: function(event, ui) {
                        $("#" + event.target.id).addClass("hovered");   
                    },
                    out: function(event, ui) {
                        $("#" + event.target.id).removeClass("hovered");
                    },
                });
            }

            // and if we have already teched fully, 
            // don't allow it to go higher
            if (match["tech"]["friendly"] < MAX_TECH) {
                $("#friendly_tech").addClass("targettable").click( function (event) {
                    trash($(".card.selected"));
                });
            }
    }


    function trash(hand_card) {

        if (match.phase != 1 && match.phase != 3) {
            //not in an interactive phase, so no clicky
            return;
        }

        //visually remove from hand
        hand_card.remove();

        tech_up(1);

        if (match.phase == 1) {
            $("input[name='card1']").val(hand_card.attr("id")); 
            $("input[name='node1']").val('tech'); 
            $("input[name='align1']").val("friendly"); 
        }
        else if (match.phase == 3) {
            $("input[name='card2']").val(hand_card.attr("id")); 
            $("input[name='node2']").val('tech'); 
            $("input[name='align2']").val("friendly"); 
        }

        next_phase();
    }

    function ai_tech_up(amount) {

        //tech up one notch
        match["tech"]["ai"] += amount; 

        if (match["tech"]["ai"] > MAX_TECH) tech_level = MAX_TECH;

        $("#ai_tech h1").text("T" + match["tech"]["ai"]);

        action_indicator($("#ai_tech"), "AI teched by " + amount);
        show_number($("#ai_tech"), amount);
    }

    function tech_up(amount) {

        //tech up one notch
        match["tech"]["friendly"] += amount; 

        if (match['tech']['friendly'] > MAX_TECH) tech_level = MAX_TECH;

        $("#friendly_tech h1").text("T" + match['tech']['friendly']);

        show_number($("#friendly_tech"), amount);
    }

    function cast(hand_card, node) { 

        if (match.phase != 1 && match.phase != 3) {
            //not in an interactive phase, so no clicky
            return;
        }

        //convert jquery element into json w/ game logic
        var card = match.hand_cards[hand_card.attr("id")];
        var align = "";

        //record it for sending to server
        if (match.phase == 1) {
            $("input[name='card1']").val(hand_card.attr("id")); 
            $("input[name='node1']").val(node.attr("name")); 
            if (node.parent().hasClass("friendly")) {
                $("input[name='align1']").val("friendly"); 
                align="friendly";
            }
            else {
                $("input[name='align1']").val("ai"); 
                align="ai";
            }
        }
        else if (match.phase == 3) {
            $("input[name='card2']").val(hand_card.attr("id")); 
            $("input[name='node2']").val(node.attr("name")); 
            if (node.parent().hasClass("friendly")) {
                $("input[name='align2']").val("friendly"); 
                align = "friendly";
            }
            else {
                $("input[name='align2']").val("ai"); 
                align = "ai";
            }
        }

        //visually remove from hand
        hand_card.remove(); 
        var card_id = hand_card.attr("id");

        cast_card('friendly', align, card, node);

        setTimeout( next_phase, 800);
    }

    function cancel_cast() {
        $(".card").removeClass("selected");

        //clear old targetting events 
        $(".node").removeClass("targettable").unbind("click");

        $("#friendly_tech").removeClass("targettable").unbind("click");
    }
