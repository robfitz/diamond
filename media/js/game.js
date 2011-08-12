function pass_turn() {

    var turn = $("textarea[name='player_turn']");
    turn.val(turn.val() + player_name + " pass\n");

    next_phase(false); 
} 

var UNIT_R = 25;

var phases = ["draw", "play_1", "attack", "play_2", "ai_draw", "ai_play_1", "ai_attack", "ai_play_2"];

// everything!
var game;
var player_name;
var opponent_name;

    function draw_starting_hand() { 
        $.ajax({ url: "/playing/first_turn/",
                success: function(data) {

                    // get model from server
                    game = eval('(' + data + ')');

                    player_name = game['player'];
                    opponent_name = get_opponent_name(game, player_name)

                    // update UI to match new game state
                    if (game['goal'] == "kill units") {
                        // mark AI as unkillable
                        // if the goal is to wipe
                        // units out 
                        $(".life.ai h1").text("∞"); 
                    }

                    for (player_name in game['players']) {
                        for_each_unit(game, 
                            player_name, 
                            function(game, player, unit) { 
                                //play(game, player, unit, player, unit.row, unit.x, true);
                                show_unit(unit);
                        });
                    }

                    // draw starting cards 
                    delay = add_cards_to_hand( game['players'][player_name]['hand'] )

                    // kick things off w/ regular turns
                    setTimeout( do_phase, delay )
                }
            }); 
    }

    function end_turn() {
        $.post("/playing/end_turn/",
            $("#current_turn").serialize(),
            function(data) {

                if (match.winner) {
                    // if the match has been won or
                    // lost, ignore how the AI responds
                    return;
                }

                turn_data = eval('(' + data + ')');

                verify_board_state(match["turn_data"]["verify_board_state_before_ai"]);

                next_phase(false);
            }
        );

        $("textarea[name='player_turn']").val("");
    }

    function verify_board_state(server_board) {

        var p1, p2;
        for (name in server_board['players']) {
            if (name != "ai") {
                p1 = name;
            }
            else {
                p2 = name;
            }
        }

        if (server_board['players'][p1]['life'] != match["life"]["friendly"]) {
            alert("different life totals, friendly (server v local): " + server_board['players'][p1]['life'] + "," + match['life']['friendly']);
        } 
        if (server_board['players'][p2]["life"] != match["life"]["ai"]) {
            alert("different life totals, ai (server v local): " + server_board['players'][p2]['life'] + "," + match['life']['ai']);
        }


        if (server_board['players'][p1]["tech"] != match["tech"]["friendly"]) {
            alert("different tech totals, friendly (server v local): " + server_board['players'][p1]['tech'] + "," + match['tech']['friendly']);
        } 
        if (server_board['players'][p2]["tech"] != match["tech"]["ai"]) {
            alert("different tech totals, ai (server v local): " + server_board['players'][p2]['tech'] + "," + match['tech']['ai']);
        }

        verify_board_state_for(server_board, p1);
        verify_board_state_for(server_board, p2);
    }
    function verify_board_state_for(server_board, align) {

        return;

        var temp_align = align;
        if (align != 'ai') temp_align = 'friendly';

        var board = server_board['players'][align]['board'];
        for (node_key in board) { 
            
            var s_node = board[node_key];
            var row = node_key.split('_')[0]
            var x = node_key.split('_')[1]

            var node_pk = board_node_pks[row][x] 
            var node = boards[temp_align]["" + node_pk];

            if ((!s_node || !s_node["type"] || s_node["type"] == "empty") && (!node || node["type"] == "empty")) {
                //both are null, that's okay
            }
            else if ((!s_node || !s_node["type"] || s_node["type"] == "empty") || (!node || node["type"] == "empty")) {
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
                    if (node.model.pk != s_node.pk) {
                        alert("server (" + s_node.pk + ") and local (" + node.model.pk + ") unit card PKs don't match");

                    }
                    
                    // same damage?
                    if (s_node.damage != node.damage()) {
                        alert("server (" + s_node.damage + ") and local (" + node.damage() + ") unit damages don't match on " + node_key + "," + align);
                    }
                }
                else if (node.type == "rubble") {
                    // same rubble amount?
                    if (s_node['fields']['rubble_duration'] != node.amount) {
                        alert("server (" + s_node['fields']['rubble_duration'] + ") and local (" + node.amount + ") rubble amounts don't match on " + node_key + "," + align);
                    } 
                }
            } 
        }
    }


function next_phase(is_first_turn) {

    game['current_phase'] ++
    if (game['current_phase'] >= phases.length) {
        game['current_phase'] = 0;
    }

    do_phase();
}

function do_phase() {

        if (is_game_over(game)) {
            var winner = is_game_over(game)
            return
        } 

        cancel_cast();


        // highlight current phase UI
        $("#phases").find("li.active").removeClass("active");
        $("#phases").find("#" + game['current_phase']).addClass("active");

        if (game['current_phase'] == 0 ) {

            heal_units(player);
            var delay = add_cards_to_hand(turn_data['player_draw'])
            setTimeout ( function() {
                next_phase();
            }, delay); 
        }
        else if (game['current_phase'] == 1) {
            if (game['players'][player_name]['hand'].length == 0) {
                // no hand cards, skip phase
                setTimeout( function() { next_phase(); }, 200); 
            }
            else {
                // cards in hand, wait for player to choose
                slider_alert("It's the first half of your turn!",
                            "Pick a card to play, tech up, or skip your turn",
                            false); 
            }
        }
        else if (game['current_phase'] == 2) {
            //begin logic for auto-attacking
            var delay = do_attack_phase(game, player_name);
            setTimeout(function() { next_phase(); }, delay);
        }
        else if (game['current_phase'] == 3) {
            if (game['players'][player_name]['hand'].length == 0) {
                setTimeout( function() { next_phase(); }, 200); 
            }
            else {
                slider_alert("It's the second half of your turn!",
                        "Pick a card to play, tech up, or skip your turn",
                        false);
                //do nothing.
                //wait for player to play card
            }
        }
        else if (game['current_phase'] == 4) {
            //ai draw & heal
            remove_one_rubble("friendly"); 
            end_turn();

            heal_units("ai");
        }
        else if (game['current_phase'] == 5 ) { 
            do_turn_move(game, 'ai', turn_data['ai_turn'][0]);
            show_turn_move(game, 'ai', turn_data['ai_turn'][0]);

            setTimeout ( function() {
                next_phase(false);
            }, 500); 
        } 
        else if (game['current_phase'] == 6) {
            //ai attack
            var delay = do_attack_phase(game, opponent_name);
            setTimeout( function() {
                    next_phase(false);
                }, delay);
        }
        else if (game['current_phase'] == 7 ) {
            do_turn_move(game, 'ai', turn_data['ai_turn'][1]);
            show_turn_move(game, 'ai', turn_data['ai_turn'][1]);

            setTimeout ( function() {
                next_phase(false);
            }, 500); 
            remove_one_rubble("ai");

            verify_board_state(turn_data["verify_board_state_after_ai"]);

            setTimeout ( function() {
                next_phase(false);
            }, 400); 

        }
    }

    function do_ai_play_1() { 

        if (match.turn_data.ai_turn[0]) {

            var action = match.turn_data.ai_turn[0]['action'];

            if (action == 'pass') {

            }
            else if (action == 'tech') {
                ai_tech_up(1); 
            }
            else if (action == 'play') {
                var card_info = match.turn_data.ai_turn[0].card;
                var node_info = match.turn_data.ai_turn[0].node;

                var align = node_info['player'];

                var node = $(".board." + node_info['player'] + " .node[name='" + node_info.row + "_" + node_info.x + "']");

                ai_cast(card_info, node, align);
            }
            else {
                //nothing to cast or tech up
                alert("do_ai_play_1: unexpected ai action: " + action);
            }
        }
    }

    function do_ai_play_2() {
        if (match.turn_data.ai_turn[1]) {

            var action = match.turn_data.ai_turn[1]['action'];

            if (action == 'pass') {

            }
            else if (action == 'tech') {
                ai_tech_up(1); 
            }
            else if (action == 'play') {

                var card_info = match.turn_data.ai_turn[1].card;
                var node_info = match.turn_data.ai_turn[1].node;

                var align = node_info['player'];

                var node = $(".board." + node_info['player'] + " .node[name='" + node_info.row + "_" + node_info.x + "']");

                ai_cast(card_info, node, align);
            }
            else {
                //nothing to cast or tech up
                alert("do_ai_play_2: unexpected ai action: " + action);
            }
        }
    } 

    /** returns the number of milliseconds this attack phase will require to animate */
    function deprecated___do_attack_phase(alignment) { 
        alert ('skipping game.js do attack phase ');
        return;

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

                var attack_path = unit.get_attack_path(board_node_pks, board_node_locs, true);

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
                                    var damaged_unit = attack_path[current_animation_step].damaged_unit;
                                    damaged_unit.show_next_damage();
                                    //animation_ms += 1000;
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
        });
        return animation_ms;
    }





function win() { 

    alert("skipping game.js win()");
    return;

    if (!match.winner) {
        setTimeout(function() { 
            $("#win_screen").show("slide", "slow"); 
            end_turn();
            }, 500);
        match.winner = 'friendly';
    }
}
function lose() {
    alert("skipping game.js lose()");
    return;

    if (!match.winner) {
        setTimeout(function() {
            $("#lose_screen").show("slide", "slow");
            }, 500);
        match.winner = 'ai';
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
            unit.gui_life = unit.remaining_life;
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

    /** 
     * returns a list of node points in format: 
     * { dx:XXX, drow:XXX, [action:damage_unit/damage_player/blocked], node_id:node_pk } 
     */ 
    function do_attack(unit, node_id, alignment) {

        alert("skipping game.js do_attack");
        return;

        if (!unit) {
            alert('attempted attack from non-existant unit at node ' + node_id + " of alignment " + alignment);
            return []; 
        }

        if (unit.model_fields.attack_type == "na"
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

        var steps_taken = 0;

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

            steps_taken ++;
            if (unit.model_fields.attack_type == "flying" && steps_taken < 3) {
                // flying units always pass over the subsequent 2 nodes
                continue;
            }

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
                    path_node.damaged_unit = collision_unit;
                    damage_unit(next_node_id, alignment, unit.attack, unit); 
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

        if (match.goal == "kill units" && alignment == "ai") {
            // enemy is immortal in kill units mode
            return;
        } 

        match.life[alignment] -= amount;

        var str = "" + match.life[alignment];
        if (amount < 10) str = " " + str;
        $(".life." + alignment + " h1").text(str);

        show_number($(".life." + alignment), -1 * amount);

    }

    function add_card_to_hand(card_json) {
        var card = get_unit_body(card_json).addClass("card").addClass("unit_piece").appendTo("#friendly_hand");

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

        if (game['current_phase'] != 1 && game['current_phase'] != 3) {
            //not in an interactive phase, so no clicky
            return;
        }

        ui.addClass("selected");

        // if the tech level is high enough, select the places
        // on the board we can use this card
        if (game['players'][player_name]["tech"] >= card_json.fields.tech_level) {
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
                    cast($(".card.selected"), $(event.target)); 
                },
                over: function(event, ui) {
                    $(event.currentTarget).addClass("hovered");   
                },
                out: function(event, ui) {
                    $(event.currentTarget).removeClass("hovered");
                },
            });
        }

        $("#friendly_tech").addClass("targettable").click( function (event) {
            trash($(".card.selected"));
        });
    }


    function trash(hand_card) {

        if (game['current_phase'] != 1 && game['current_phase'] != 3) {
            //not in an interactive phase, so no clicky
            return;
        }

        //visually remove from hand
        hand_card.remove();

        tech_up(1);

        var turn = $("textarea[name='player_turn']");
        turn.val(turn.val() + player_name + " tech " + hand_card.attr('id') + "\n"); 

        next_phase(false);
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

        if (game['current_phase'] != 1 && game['current_phase'] != 3) {
            //not in an interactive phase, so no clicky
            return;
        }

        var card = get_hand_card(game, player_name, hand_card.attr("id"));
        var target_owner;

        if (node.parent().hasClass("friendly")) {
            target_owner = player_name;
        }
        else {
            target_owner = opponent_name;
        }

        var node_loc = node.attr("name")
        var r = parseInt(node_loc.split("_")[0])
        var x = parseInt(node_loc.split("_")[1])

        // turn format: player action [card [node_owner row x]]
        var this_turn = player_name + " play " + hand_card.attr('id') + " " + target_owner + " " + row + " " + x + "\n"; 

        var turn = $("textarea[name='player_turn']");
        turn.val(turn.val() + this_turn);

        play(game, player_name, card, target_owner, r, x, false);

        next_phase();
    }

    function cancel_cast() {
        $(".card").removeClass("selected");

        //clear old targetting events 
        $(".node").removeClass("targettable").unbind("click");

        $("#friendly_tech").removeClass("targettable").unbind("click");
    }
