"use strict";
/* REST call loading */
$(document).on({
    ajaxStart: function() {
        $('#error-msg-display').hide();
        $('.modal').show();
        $('#end_date_input').css('border', 'solid 1px #DDD');
        $('#start_date_input').css('border', 'solid 1px #DDD');
    },
    ajaxStop: function() {
        $('.modal').hide();
    }
});

$(document).keypress(function(e) {
    if (e.which == 13) {
        load_graph();
    }
});

$(function() {
    $('#start_date').datetimepicker({
        format: 'YYYY-MM-DD HH:00:00'
    });
    $('#end_date').datetimepicker({
        useCurrent: false, //Important! See issue #1075
        format: 'YYYY-MM-DD HH:00:00'
    });
    $("#start_date").on("dp.change", function(e) {
      //  $('#end_date').data("DateTimePicker").minDate(e.date.subtract(1,"days"));
        $('#start_date_input').css('border', 'solid 1px #DDD');
            //$(this).data("DateTimePicker").hide();
    });
    $("#end_date").on("dp.change", function(e) {
       // $('#start_date').data("DateTimePicker").maxDate(e.date);
        $('#end_date_input').css('border', 'solid 1px #DDD');
            //$(this).data("DateTimePicker").hide();
    });
});

$(document).ready(function() {
    $('#load-graph-btn').on('click', function() {
        load_graph();
    });
    $('.hide-btn').on('click', function() {
        var button = $(this)
        var id = $(this).attr("id")
        $(button).parent().parent().parent().remove();
        if (id == 'read-me') {
            //expand control div
            $('.control').attr('class', 'col-md-12 control');
        }
    });

    $('.graph-selector').on('click', function() {
        //work out how to put the top level dropdown text in later
        $('#current-graph-label').text($(this).text().trim())
        $('#current-graph-label').attr('class', 'label label-info')
    });

});


/* load graph from endpoint */
function load_graph(groupby) {
    if (groupby) {
        groupby = $(groupby).text()
    } else {
        groupby = null
    }

    var graph = $('#current-graph-label').text();
    if (graph == "No Graph Selected") {
        display_err_msg("please select a graph from the dropdown above");
        return;
    }

    var start_date = $('#start_date').data("DateTimePicker").date();
    var end_date = $('#end_date').data("DateTimePicker").date();

    if (!check_dates(start_date, end_date)) {
        return;
    }

    if (start_date) {
        start_date = start_date.format("YYYY-MM-DD HH:00:00")
    }
    if (end_date) {
        end_date = end_date.format("YYYY-MM-DD HH:00:00")
    }


    //more date checking needed, startdate cannot be more than 90 days ago, end date cannot be greater than today. 

    var url = "/dashboard/" + graph + "?start_date=" + start_date + "&end_date=" + end_date + "&groupby=" + groupby;
    //get rid of all old graphs
    $('.graph-area').empty();

    //send request
    $.ajax({
        url: url,
        type: "GET",
        success: function(data) {
            //append graph to bottom of body
            $('.graph-area').append(data);
        },
        error: function(data) {
            ($('#error-msg').empty()).append(data.responseText);
            $('#error-msg-display').show();
        }
    });
}

function check_dates(start_date, end_date) {
    //return null if return
    var min_start = moment().subtract(90, "days");
    var ok = true;
    var err_text = ""

    if (start_date != null) {
        if (start_date < min_start) {
            //start date shouldn't be more than 90 days ago
            err_text += "start date cannot be more than 90 days ago</br>";
            $('#start_date_input').css('border', 'solid 2px red')
            ok = false;
        }
        if (start_date >= moment().add(1, "days")) {
            err_text += "start date cannot be in the future</br>";
            $('#start_date_input').css('border', 'solid 2px red')
            ok = false;
        }
    }

    if (end_date != null) {
        if (end_date < min_start) {
            //start date shouldn't be more than 90 days ago
            err_text += "end date cannot be more than 90 days ago</br>";
            $('#end_date_input').css('border', 'solid 2px red')
            ok = false;
        }
        if (end_date >= moment().add(1, "days")) {
            //end date cant be greater than today
            err_text += "end date cannot be in the future</br>";
            $('#end_date_input').css('border', 'solid 2px red')
                //1px solid #ccc
            ok = false;
        }
    }

    if(start_date != null && end_date != null){
        if(start_date > end_date){
            err_text += "start date cannot be greater than the end date</br>";
            $('#start_date_input').css('border', 'solid 2px red')
                //1px solid #ccc
            ok = false;
        }
        if(end_date < start_date){
            err_text += "end date cannot start before the start date</br>";
            $('#end_date_input').css('border', 'solid 2px red')
            ok = false;
        }
    }

    //don't need to check this anymore
    /*
    var date_regex = /^\d{4,4}-\d{2,2}-\d{2,2} \d{2,2}:\d{2,2}:\d{2,2}$/;

    var valid_start_date = date_regex.exec(start_date);
    var valid_end_date = date_regex.exec(end_date);
    */
    display_err_msg(err_text)
    return ok;
}


function display_err_msg(text) {
    ($('#error-msg').empty()).append(text);
    $('#error-msg-display').show();
}

function remove_button(button) {
    $(button).parent().parent().parent().remove();
}
