function pass_turn() {

    var turn = $("textarea[name='player_turn']");
    turn.val(turn.val() + player_name + " pass\n");

    game['current_phase'] ++; 
    qfx({'action': 'next_phase'});
    on_next_player_action(game, player_name);
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

                for (var p in game['players']) {
                    for_each_unit(game, 
                        p, 
                        function(game, player, unit) { 
                            show_unit(unit);
                    });
                }

                var hand = game['players'][player_name]['hand'];
                game['players'][player_name]['hand'] = [];
                // draw starting cards 
                do_player_turn_1(game, player_name, hand);
            }
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
        if (game['players'][player_name]["current_tech"] >= card_json.fields.tech_level) {
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

            if (card_json['fields']['defense'] > 0) {
                targets.mouseenter( function ( e ) { 

                    var name = $(this).attr("name");
                    var row = parseInt(name.split("_")[0]);
                    var x = parseInt(name.split("_")[1]);

                    var node = $(e.currentTarget);

                    var path = get_attack_path(game, player_name, card_json['fields']['attack_type'], row, x);

                    draw_attack_path(player_name, path); 
                });
            }

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

        var player = player_name;
        var card = get_hand_card(game, player, hand_card.attr("id"));

        discard(game, player, card);
        tech(game, player, 1);

        var turn = $("textarea[name='player_turn']");
        turn.val(turn.val() + player_name + " tech " + hand_card.attr('id') + "\n"); 

        qfx({'action': 'next_phase'});
        game['current_phase'] ++; 
        on_next_player_action(game, player_name);

        cancel_cast(); 
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

        var target_owner = (node.parent().hasClass("friendly") ? player_name : opponent_name);

        var node_loc = node.attr("name")
        var r = parseInt(node_loc.split("_")[0])
        var x = parseInt(node_loc.split("_")[1])

        var this_turn = player_name + " play " + hand_card.attr('id') + " " + target_owner + " " + r + " " + x + "\n"; 

        var turn = $("textarea[name='player_turn']");
        turn.val(turn.val() + this_turn);

        play(game, player_name, card, target_owner, r, x, false);

        qfx({'action': 'next_phase'});
        game['current_phase'] ++; 
        on_next_player_action(game, player_name);

        cancel_cast();
    }

    function cancel_cast() {
        $(".card").removeClass("selected");

        //clear old targetting events 
        $(".node").removeClass("targettable").unbind("click").unbind("mouseenter");

        $("#friendly_tech").removeClass("targettable").unbind("click");
    }
