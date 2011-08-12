animation_example = [ { action: 'move', target: { player: 'ai', row: 2, x: 1 }, value: { 'row': -1, 'x': 0 } },
    { action: 'damage_unit', target: { player: 'ai', row: 2, x: 1 }, value: 1 },
    { action: 'heal_unit', target: { player: 'ai', row: 2, x: 1 }, value: 1 },
    { action: 'remove_rubble', target: { player: 'ai', row: 2, x: 1 }, value: 1 },
    { action: 'damage_player', target: { player: 'ai' }, value: 1 },
    { action: 'add_unit', target: { player: 'ai', row: 2, x: 1 }, value: { type: 'unit', pk: 123, fields: { stuff: 'stuff' } } },
    { action: 'remove_unit', target: { player: 'ai', row: 2, x: 1 }, value: null },
    { action: 'add_rubble', target: { player: 'ai', row: 2, x: 1 }, value: null },
    { action: 'remove_rubble', target: { player: 'ai', row: 2, x: 1 }, value: null }
    ]

var DEFAULT_DELAY = 200;

var durations = { 
    'discard': 200,
    'draw': 200,
    'damage_unit': 0,
    'heal_unit': 0,
    'draw': 200,
    'move': 200,
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
        alert("unknown player alignment in get_node_view: " + player);
    }

    return $(".board." + alignment + " .node[name='" + row + "_" + x + "']");
}


var effects_queue = [];
var is_effects_playing = false;

// qfx == queue fx == queue effects
function qfx(effect) {

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

    switch (action) {
        case 'discard':
            // remove visuals from hand view
            $("#friendly_hand #" + effect['value']['pk']).remove();
            $("#friendly_hand .card").removeClass("selected"); 
            break;
        case 'tech': 
            // +1 message on player tech
            // increase tech #
            break;
        case 'move':
            // scoot the unit by delta * step size
            var row = effect['delta']['row'];
            var x = effect['delta']['x'];
            var d_row = (row < 0 ? "-=" : "+=") + (100*Math.abs(row));
            var d_x = (x < 0 ? "-=" : "+=") + (100*Math.abs(x));

            var node = get_node_view(effect['target']['player'], effect['target']['row'], effect['target']['x']);

            node.animate( 
                    {
                        top: d_row,
                        left: d_x,
                        "z-index": 2 
                    },
                    { duration: get_delay(effect) }
                    );

            //alert('delaying for: ' + get_delay(effect));

            break;
        case 'damage_unit':
            // -1 on target
            // shake target
            break;
        case 'remove_unit':
            // explode target
            // remove target from screen
            break;
        case 'add_rubble':
            // place rubble w/ animation ( handled by unit? )
            break;
        case 'add_unit': 
            // place unit w/ animation
            show_unit(effect['value']);
            break;
        default:
            alert('unknown action while doing FX: ' + action);
    } 

    
    setTimeout( play_remaining_effects, get_delay(effect) ); 
}


function get_delay(effect) { 
    var delay = DEFAULT_DELAY;
    try {
        delay = durations[action]
    } catch (error) {
        alert("found no delay for " + delay);
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

        var path = get_attack_path(game, model);
        draw_attack_path(unit, path); 
    });

    node.mouseleave(function ( e ) {
            clear_attack_paths();
    });

}

function get_unit_body(model, alignment) {
    var model_fields = model.fields;
    var unit_piece = $("<div title='" + model_fields.tooltip + "' class='attack_" + model_fields.attack + "' id='" + model.pk + "'></div>");

    var url = "";
    if (alignment == game['player'] && model_fields.icon_url_back) {
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

function add_cards_to_hand(cards) {
    //draw cards
    var i = 0;
    while (i < cards.length) {
        var card = cards[i] // necessary local for
            // proper state in the timeout closure
            
        setTimeout ( function() {
            add_card_to_hand( card );
        }, 200 * (i+1));
        i ++; 
    }
}

function add_card_to_hand(card_model) {

    var card = get_unit_body(card_model).addClass("card").addClass("unit_piece").appendTo("#friendly_hand");

    init_tooltips("#friendly_hand");

    card.draggable({ 
        start: function(event, ui) { 
            begin_card_drag(event, card, card_model); 
        },
        revert: "invalid",
        //snap: ".node",
        //snapMode: "inner",
    });

    card.click( function(event) {
        begin_card_drag(event, card, card_model); 
    });
}
