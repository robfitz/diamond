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
