var match = {
    tech: { friendly: 1, ai: 1 },
    life: { 
        'friendly': 10, 
        'ai': 10 
    },
    phase: -1,

    //hand_cards[card_pk] = card.fields
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
                match.turn_data = eval('(' + data + ')');
                next_phase();
            }
        );
    }

    function next_phase() {
        next_phase(false);
    }

    function next_phase(is_first_turn) {

        match.phase ++;
        cancel_cast();

        //alert("phase: " + match.phase);

        if (match.phase >= phases.length) {
            match.phase = 0;
            $("#phases li.active").removeClass("active").siblings().first().addClass("active");
        }
        else {
            $("#phases li.active").removeClass("active").parent().children().eq(match.phase).addClass("active");
        }

        if (match.phase == 0 || is_first_turn) {
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
        if (match.phase == 1) {
            //do nothing.
            //wait for player to play card
        }
        if (match.phase == 2) {
            //begin logic for auto-attacking
            var delay = do_attack_phase("friendly");
            setTimeout(next_phase, delay);
        }
        if (match.phase == 3) {
            //do nothing.
            //wait for player to play card
        }
        if (match.phase == 4) {
            //ai draw & heal
            heal_units("ai");

            end_turn();
        }
        if (match.phase == 5 || is_first_turn) {
            if (match.turn_data.ai_turn[0]) {
                //ai play 1
                if (match.turn_data.ai_turn[0].fields.is_tech_1) {
                    ai_tech_up(1); 
                    if (!is_first_turn) next_phase();
                }
                else if (match.turn_data.ai_cards[0]) {
                    var ai_play = match.turn_data.ai_cards[0].fields;
                    var target = match.turn_data.ai_turn[0].fields.target_node_1;
                    var align = match.turn_data.ai_turn[0].fields.target_alignment_1; 
                    //ai summons
                    var node = $(".board.ai .node[name='" + target + "']");
                    ai_cast(ai_play, node);
                    if (!is_first_turn) next_phase();
                }
                else {
                    //nothing to cast or tech up
                }
            }
        } 
        if (match.phase == 6) {
            //ai attack
            var delay = do_attack_phase("ai");
            setTimeout(next_phase, delay);
        }
        if (match.phase == 7 || is_first_turn) {
            if (match.turn_data.ai_turn[0]) {
                //ai play 2
                if (match.turn_data.ai_turn[0].fields.is_tech_2) {
                    ai_tech_up(1); 
                    if (!is_first_turn) next_phase();
                }
                else if (match.turn_data.ai_cards[1]) {
                    var ai_play = match.turn_data.ai_cards[1].fields;
                    var target = match.turn_data.ai_turn[0].fields.target_node_2;
                    var align = match.turn_data.ai_turn[0].fields.target_alignment_2; 
                    var node = $(".board.ai .node[name='" + target + "']");
                    ai_cast(ai_play, node);
                    if (!is_first_turn) next_phase();
                }
                else {
                    //nothing to cast or tech up
                }
            }
        }
    }

    /** returns the number of milliseconds this attack phase will require to animate */
    function do_attack_phase(alignment) { 
        var i = 0;
        var animation_ms = 0;
        $(".board." + alignment + " .node.unit").each( 
            function () { 
                var approach_dir = (alignment == "friendly" ? "-":"+");
                var retreat_dir = (alignment == "friendly" ? "+":"-");

                var to_animate = $(this);

                //find target
                //var attacker_id = to_animate.attr("id");
                var node_id = to_animate.attr("name");

                var attacker_json = boards[alignment][node_id];

                var attack_path = do_attack(attacker_json, node_id, alignment);

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
                                    damage_player(opponent_alignment, attacker_json.attack);
                                }
                                else if (action == "damage_unit") {
                                    damage_unit(target_node_pk, opponent_alignment, attacker_json.attack); 
                                } 

                                // i have no idea if this will work
                                attack_path = do_attack(attacker_json, node_id, alignment);

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
        });
        return animation_ms;
    }

    function set_unit_damage(node_pk, alignment, total_damage) {
        var unit = boards[alignment][node_pk];

        if (!unit) return;

        unit.damage = total_damage;

        var node = $(".board." + alignment + " .node[name='" + node_pk + "']");
        node.children(".unit_piece").html(unit.attack + "/" + (unit.defense - unit.damage) + unit.attack_type[0]); 

        if (unit.damage >= unit.defense) {
            //killed. remove from board.
            boards[alignment][node_pk] = null;
            node.children(".unit_piece").remove(); 
            node.addClass("empty");
            node.removeClass("unit");
        } 
    }
    function damage_unit(node_pk, alignment, delta_damage) {
        var unit = boards[alignment][node_pk];

        if (!unit) return;

        if (!unit.damage) {
            unit.damage = 0;
        }
        set_unit_damage(node_pk, alignment, unit.damage + delta_damage); 
    }
    function heal_units(alignment) {
        for (var node_pk in boards[alignment]) {
            var node = boards[alignment][node_pk];
            set_unit_damage(node_pk, alignment, 0);
        }
    }

    function ai_cast(card, node) { 
        var align = (card.target_alignment == "enemy" ? "friendly" : "ai"); 
        cast_card(align, card, node); 
    }

    function cast_card(target_alignment, card, node) {

        if (card.target_aiming == "all") {
            nodes = node.parent().children(".empty");
        }
        else if (card.target_aiming == "chosen") {
            nodes = node
        }
        else {
            alert('unknown card target aiming: ' + card.target_aiming);
        }

        for (var i = 0; i < nodes.length; i ++) {
            node = nodes.eq(i);

            if (card.direct_damage) {
                damage_unit(node.attr('name'), target_alignment, card.direct_damage); 
            }
            if (card.defense) { 

                //create a summon
                node.addClass("unit");
                node.addClass("occupied"); 

                node.removeClass("empty");

                //for lookup of unit behaviour later
                node.attr("id", card.pk);

                match.played_cards[card.pk] = card; 
                boards[target_alignment][node.attr("name")] = $.extend(true, {}, card);

                node.children(".unit_piece").remove();
                var unit = $("<div class='unit_piece' id='" + card.pk + "'>" + card.attack + "/" + card.defense + card.attack_type[0] + "</div>").appendTo(node);

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
    function do_attack(card_json, node_id, alignment) {

        if (card_json.attack == 0
            || card_json.attack_type == "wall"
            || card_json.attack_type == "defender") {

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
            if (collision_unit) {
                if (alignment == starting_alignment) { 

                    //am i ranged? loop!
                    if (card_json.attack_type == "ranged") {
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

                attack = card_json.attack;
                path_node.action = "damage_player";
                //damage_player(alignment, attack); 
            }
            else {
                //not the player and no unit there. loop
            } 
        } 
        return path_info;
    }

    function set_player_life(alignment, amount) { 
        match.life[alignment] = amount;
        $(".life." + alignment + " h1").text("" + match.life[alignment]);
    }

    function damage_player(alignment, amount) {
        match.life[alignment] -= amount;
        $(".life." + alignment + " h1").text("" + match.life[alignment]);
    }

    function add_card_to_hand(card_json) {
        var card = $("<li class='card' id='" + card_json.pk + "'>T" + card_json.fields.tech_level + " " + card_json.fields.name + "</li>").appendTo("#friendly_hand");

        match.hand_cards[card_json.pk] = card_json.fields;

        card.click( function(event) {

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

            $(this).addClass("selected");

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
                    cast($(".card.selected"), $(this));
                });
            }

            // and if we have already teched fully, 
            // don't allow it to go higher
            if (match["tech"]["friendly"] < MAX_TECH) {
                $("#friendly_tech").addClass("targettable").click( function (event) {
                    trash($(".card.selected"));
                });
            }
        });
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
    }
    function tech_up(amount) {

        //tech up one notch
        match["tech"]["friendly"] += amount; 

        if (match['tech']['friendly'] > MAX_TECH) tech_level = MAX_TECH;

        $("#friendly_tech h1").text("T" + match['tech']['friendly']);
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

        cast_card(align, card, node);

        next_phase();
    }

    function cancel_cast() {
        $(".card").removeClass("selected");

        //clear old targetting events 
        $(".node").removeClass("targettable").unbind("click");

        $("#friendly_tech").removeClass("targettable").unbind("click");
    }
