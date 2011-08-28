function pass_turn() {

    var turn = $("textarea[name='player_turn']");
    turn.val(turn.val() + player_name + " pass\n");

    qfx({'action': 'next_phase'});
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

            turn_data = eval('(' + data + ')');

            // verify_board_state(match["turn_data"]["verify_board_state_before_ai"]); 

            qfx({'action': 'next_phase'});
        }
    );

    $("textarea[name='player_turn']").val("");
}



function next_phase() {

    game['current_phase'] ++
    if (game['current_phase'] >= phases.length) {
        game['current_phase'] = 0;
    }

    do_phase();
}

function do_phase() {

    if (is_game_over(game)) {
        var winner = is_game_over(game)
        if (winner == player_name) {
            qfx({ 'action': 'win' });
        }
        else {
            qfx({ 'action': 'lose' });
        } 
        return;
    } 

    cancel_cast(); 

    // highlight current phase UI
    $("#phases").find("li.active").removeClass("active");
    $("#phases").find("#" + game['current_phase']).addClass("active");

    if (game['current_phase'] == 0 ) {

        heal(game, player_name);

        add_cards_to_hand(turn_data['player_draw'])

        qfx({'action': 'next_phase'});
    }
    else if (game['current_phase'] == 1) {
        if (game['players'][player_name]['hand'].length == 0) {
            // no hand cards, skip phase
            qfx({'action': 'next_phase'});
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
        do_attack_phase(game, player_name);

        if (is_game_over(game)) {
            var winner = is_game_over(game);
            if (winner == player_name) {
                qfx({ 'action': 'win' });
            }
            else {
                qfx({ 'action': 'lose' });
            } 
            return;
        }

        qfx({'action': 'next_phase'});
    }
    else if (game['current_phase'] == 3) { 
        if (game['players'][player_name]['hand'].length == 0) {
            qfx({'action': 'next_phase'});
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
        remove_rubble(game, player_name);
        end_turn();

        heal(game, opponent_name);
    }
    else if (game['current_phase'] == 5 ) { 
        do_turn_move(game, 'ai', turn_data['ai_turn'][0]); 
        qfx({'action': 'next_phase'});
    } 
    else if (game['current_phase'] == 6) {
        //ai attack
        do_attack_phase(game, opponent_name);
        qfx({'action': 'next_phase'});
    }
    else if (game['current_phase'] == 7 ) {
        do_turn_move(game, 'ai', turn_data['ai_turn'][1]);

        qfx({'action': 'next_phase'});
        remove_rubble(game, opponent_name);

        // verify_board_state(turn_data["verify_board_state_after_ai"]);

        qfx({'action': 'next_phase'}); 
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

    function ai_cast(card, node, alignment, is_first_turn) { 
        cast_card('ai', alignment, card, node, is_first_turn); 

        action_indicator(node, "AI cast " + card.fields.name);
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

        qfx({'action': 'next_phase'});
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

        qfx({'action': 'next_phase'});
    }

    function cancel_cast() {
        $(".card").removeClass("selected");

        //clear old targetting events 
        $(".node").removeClass("targettable").unbind("click");

        $("#friendly_tech").removeClass("targettable").unbind("click");
    }
