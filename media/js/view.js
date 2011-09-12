animation_example = [ { action: 'move', target: { player: 'ai', row: 2, x: 1 }, value: { 'row': -1, 'x': 0 } },
    { action: 'damage_unit', target: { player: 'ai', row: 2, x: 1 }, value: 1 },
    { action: 'heal_unit', target: { player: 'ai', row: 2, x: 1 }, value: 1 },
    { action: 'remove_rubble', target: { player: 'ai', row: 2, x: 1 }, value: 1 },
    { action: 'damage_player', target: { player: 'ai' }, value: 1 },
    { action: 'add_unit', target: { player: 'ai', row: 2, x: 1 }, value: { type: 'unit', pk: 123, fields: { stuff: 'stuff' } } },
    { action: 'remove_unit', target: { player: 'ai', row: 2, x: 1 }, value: null },
    { action: 'add_rubble', target: { player: 'ai', row: 2, x: 1 }, value: null },
    ]

var DEFAULT_DELAY = 200;

var durations = { 
    'discard': 200,
    'draw': 200,
    'damage_unit': 200,
    'heal_unit': 200,
    'draw': 200,
    'move': 200,
    'lose': 0,
    'win': 0,
    'next_phase': 0,
    'tech': 0,
} 
function get_jq(effect) { 

    return get_node_view(effect['target']['player'],
            effect['target']['row'],
            effect['target']['x']); 
}

function get_node_view(player, row, x) { 

    alignment = null;

    if (player == 'friendly' || player == 'ai') {
        alignment = player;
    }
    else if (player == player_name) {
        alignment = 'friendly';
    }
    else if (player == opponent_name) {
        alignment = 'enemy';
    }
    else {
    }

    return $(".board." + alignment + " .node[name='" + row + "_" + x + "']");
}


var effects_queue = [];
var is_effects_playing = false;

var is_qfx_prevent_enqueues = false;

function qfx_game_over() {
    is_qfx_prevent_enqueues = true;
} 

// qfx == queue fx == queue effects
function qfx(effect) {

    if (is_qfx_prevent_enqueues) {
        return;
    }

    $(".debug").text(effect['action'] + "\n" + $(".debug").text());

    effects_queue.splice(effects_queue.length, 0, effect); 

    if ( ! is_effects_playing) {
        is_effects_playing = true;
        play_remaining_effects();
    }
}

// pop the next effect off the queue, do it,
// and then begin a delay for the next item.
// will continue calling itself after delays
// until queue is empty, at which point it can
// be restarted with a call to queue_effects()
function play_remaining_effects() {

    if ( ! effects_queue || effects_queue.length == 0) {
        is_effects_playing = false;
        return;
    }

    // dequeue next effect to play
    var effect = effects_queue[0];
    effects_queue.splice(0, 1);

    action = null;
    try {
        action = effect['action'];
    }
    catch ( error ) {
        alert("null effect or missing action: " + effect + " w/ act: " + effect['action']);
        action = null;
    }

    if (! effect || ! action) {
        alert("missing effect or action");
        play_remaining_effects(); 
        return;
    } 

    var node_jq;
    try {
        node_jq = get_jq(effect);
        while (node_jq.queue().length > 0) {
            node_jq.stop(false, true);
        }
    } catch(error) {
        node_jq = null;
    }

    switch (action) {
        case 'discard':
            // remove visuals from hand view
            $("#friendly_hand #" + effect['value']['pk']).remove();
            $("#friendly_hand .card").removeClass("selected"); 
            break;
        case 'draw':
            // add visuals to hand
            if (effect['target'] != player_name) { 
                alert("someone other than player tryign to draw");
            }
            else { 
                var card_model = effect['delta'];
                var card = get_unit_body(card_model).addClass("card").addClass("unit_piece").appendTo("#friendly_hand");

                init_tooltips("#friendly_hand");

                card.draggable({ 
                    start: function(event, ui) { 
                        begin_card_drag(event, card, card_model); 
                    },
                    revert: "invalid",
                }); 
                card.click( function(event) {
                    begin_card_drag(event, card, card_model); 
                });
            }
            break;

        case 'use_tech':
            // temporarily spending some of the current tech supply
            var tech = $("." + effect['target'] + "_tech"); 
            var current = tech.find(".remaining");
            var current_shown = parseInt(current.text());
            current.text(current_shown - effect['delta']); 
            show_number(tech, -1 * effect['delta']);
            break;

        case 'refill_tech':
            // refilling the temporary supply of tech to max
            var tech = $("." + effect['target'] + "_tech"); 
            tech.find(".remaining").text( tech.find(".total").text() );
            show_number(tech, effect['delta']);
            break;

        case 'tech': 
            // permanently change the max tech level
            var tech = $("." + effect['target'] + "_tech"); 

            //increase both the current and total tech levels
            var current_shown = parseInt(tech.find(".total").text());
            tech.find(".total").text(current_shown + effect['delta']); 

            // +1 message on player tech
            show_number(tech, effect['delta']);
            break;

        case 'move':
            // scoot the unit by delta * step size
            var row = effect['delta']['row'];
            var x = effect['delta']['x'];
            var d_row = (row < 0 ? "-=" : "+=") + (100*Math.abs(row));
            var d_x = (x < 0 ? "-=" : "+=") + (100*Math.abs(x));

            node_jq.animate( 
                    {
                        top: d_row,
                        left: d_x,
                        "z-index": 2 
                    },
                    { duration: get_delay(effect) }
                ); 
            break;

        case 'damage_unit':
            
            if (effect['delta'] != 0) {
                // -1 on target
                show_number(node_jq, -1 * effect['delta']); 
                // fill in damage bubbles
                for (var i = 0; i < effect['delta']; i ++) {
                    node_jq.find(".defense_point:first").removeClass('defense_point').addClass('damage_point');
                }
                // shake
                // node_jq.stop(true, true);
                node_jq.effect("bounce", "fast"); 
            }
            break;

        case 'heal_unit':
            if (effect['delta'] != 0) {
                show_number(node_jq, effect['delta']);
                //clear damage bubbles
                node_jq.find(".damage_point").each( function () {
                        $(this).removeClass("damage_point").addClass("defense_point");
                });
            }
            break; 

        case 'remove_unit':
            // explode target
            // node_jq.stop(true, true);
            node_jq.find(".unit_piece").hide("explode", function() {
                    // remove target from screen
                    $(this).remove();
                });
            node_jq.removeClass("unit").removeClass("occupied").addClass("empty");
            break;

        case 'remove_rubble':
            // remove rubble
            // node_jq.stop(true, true);
            node_jq.find(".rubble").fadeOut(function() {
                    $(this).remove();
                });
            node_jq.removeClass("rubble").removeClass("occupied").addClass("empty");
            show_message(node_jq, "-1");
            break;

        case 'summoning_sickness_complete':
            show_message(node_jq, "Ready for combat");
            break;

        case 'add_rubble':
            // node_jq.stop(true, true);
            node_jq.addClass("rubble").addClass("occupied").removeClass("unit").removeClass("empty");
            node_jq.children().remove();
            $("<div title='Rubble appears when units dies and blocks new units from being placed for a turn' class='rubble r_1'><img src='/media/units/rubble.png'></div>").appendTo(node_jq);
            break;

        case 'add_unit': 
            // place unit w/ animation
            show_unit(effect['value']);
            break;

        case 'win':
            $("#slider_alert").hide();
            $("#win_screen").show("slide", "slow");
            break;

        case 'lose':
            $("#slider_alert").hide();
            $("#lose_screen").show("slide", "slow");
            break;

        case 'next_phase':
            $("#phases li.active").removeClass("active");
            $("#phases li:eq(" + effect['delta'] + ")").addClass("active"); 
            break;

        case 'alert':
            slider_alert(effect['target']['title'],
                    effect['target']['contents'],
                    effect['target']['wait_for_confirm']);
            break; 

        case 'damage_player':
            if (effect['target'] == 'ai'
                    && game['goal'] == 'kill units') {
                alert("trying to damage invuln ai in puzzle");
            }
            else {
                var life_h1 = $("." + effect['target'] + "_life h1");
                var current_shown_life = parseInt(life_h1.text());
                life_h1.text(current_shown_life - effect['delta']); 
                show_number(life_h1.parent(), -1 * effect['delta']); 
            }
            break;

        default:
            alert('unknown action while doing FX: ' + action);
            break;
    } 

    setTimeout( play_remaining_effects, get_delay(effect) ); 
}


function get_delay(effect) { 
    var delay = DEFAULT_DELAY;
    try {
        delay = durations[effect['action']];
    } catch (error) {
        alert("found no delay for " + effect['action']);
        delay = DEFAULT_DELAY;
    }
    return delay;
}

function show_unit(model) {

    //init and add to board

    var alignment = model['player']

    var node = get_node_view(alignment, model.row, model.x);
    node.addClass("unit");
    node.addClass("occupied"); 
    node.removeClass("empty"); 
    node.attr("id", model.pk);

    node.children(".unit_piece").remove();
    
    var unit_piece = get_unit_body(model, alignment).appendTo(node);
    unit_piece.addClass("unit_piece");

    init_tooltips(".node");

    var w = parseInt(unit_piece.css('width'));
    var h = parseInt(unit_piece.css('height'));

    var node_w = parseInt(node.css('width'));
    var node_h = parseInt(node.css('height'));

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

    show_message(node, model.fields.name);

    node.mouseenter( function ( e ) { 
        var node = $(e.currentTarget);

        var path = get_attack_path(game, alignment, model['fields']['attack_type'], model.row, model.x);

        draw_attack_path(alignment, path); 
    });

    node.mouseleave(function ( e ) {
            clear_attack_paths();
    });

}

function get_unit_body(model, alignment) {
    var model_fields = model.fields;
    var unit_piece = $("<div title='" + model_fields.tooltip + "' class='attack_" + model_fields.attack + "' id='" + model.pk + "'></div>");

    var url = "";
    try {
        if (alignment == game['player'] && model_fields.icon_url_back) {
            url = model_fields.icon_url_back;
        } 
        else {
            url = model_fields.icon_url;
        }
    } catch (error) {
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
    for (var i = 0; i < model_fields.defense; i ++) {
        $("<div class='defense_point health'></div>").appendTo(def); 
    }

    $("<div class='card_name'>T" + model.fields.tech_level + ":" + model.fields.name + "</div>").appendTo(unit_piece);

    return unit_piece;
}

function draw_attack_path(alignment, path) { 

    clear_attack_paths();
    
    for (var i = 0; i < path.length; i ++) { 
        var node = path[i];
        var dir = (node.alignment == alignment ? "attacking_from" : "attacking_to");

        if (node.alignment != "ai") {
            node.alignment = "friendly";
        }

        if (i == path.length - 1) {
            // last node should show action, not movement

            if (node.action == "damage_unit") {
                $("." + node.alignment + " .r" + node.row + ".x" + node.x + " .unit_piece").addClass("hostile_targetting"); 
            }
            else if (node.aciton == "damage_player") {
                $("." + node.alignment + " .r" + node.row + ".x" + node.x + " ." + dir).show(); 
            } 
        }
        else { 
            $("." + node.alignment + " .r" + node.row + ".x" + node.x + " ." + dir).show(); 
        }
    } 
}

function clear_attack_paths() {
    $(".attacking_from, .attacking_to").hide();
    $(".unit_piece").removeClass("hostile_targetting");
}


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
