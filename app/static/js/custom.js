// to get current year
function getYear() {
    var currentDate = new Date();
    var currentYear = currentDate.getFullYear();
    document.querySelector("#displayYear").innerHTML = currentYear;
}

getYear();


// isotope js
$(window).on('load', function () {
    $('.filters_menu li').click(function () {
        $('.filters_menu li').removeClass('active');
        $(this).addClass('active');

        var data = $(this).attr('data-filter');
        $grid.isotope({
            filter: data
        })
    });

    var $grid = $(".grid").isotope({
        itemSelector: ".all",
        percentPosition: false,
        masonry: {
            columnWidth: ".all"
        }
    })
});

// nice select
$(document).ready(function() {
    $('select').niceSelect();
  });

// client section owl carousel
$(".client_owl-carousel").owlCarousel({
    loop: true,
    margin: 0,
    dots: false,
    nav: true,
    navText: [],
    autoplay: true,
    autoplayHoverPause: true,
    navText: [
        '<i class="fa fa-angle-left" aria-hidden="true"></i>',
        '<i class="fa fa-angle-right" aria-hidden="true"></i>'
    ],
    responsive: {
        0: {
            items: 1
        },
        768: {
            items: 2
        },
        1000: {
            items: 2
        }
    }
});

$('a.thumbnail').click(function () {
    $('#productImage').attr('src',$(this).children('img').attr('src').replace('60/60','400/200'));
});

$('a.cont_shopping').click(function(){
    $('.mini_cart_section').hide();
});

$("a.edit-ship").click(function(){
    if ($("#ship-frm").css("display") == "none"){
        $("#collapseOne").addClass("show");
        $("#ship-frm").show("slow");
        $("#ship-worked").hide("slow");
        $("#ship-cancel").toggle();
    }    
});

$("a.cancel-ship").click(function(){
    if ($("#ship-worked").css("display") == "none"){
        $("#ship-worked").show("slow");
        $("#ship-frm").hide("slow");
        $("#ship-cancel").toggle();
    }    
});

$("a.edit-bill").click(function(){
    if ($("#bill-frm").css("display") == "none"){
        $("#collapseTwo").addClass("show");
        $("#bill-frm").show("slow");
        $("#bill-worked").hide("slow");
        $("#bill-cancel").toggle();
    }    
});

$("a.cancel-bill").click(function(){
    if ($("#bill-worked").css("display") == "none"){
        $("#bill-worked").show("slow");
        $("#bill-frm").hide("slow");
        $("#bill-cancel").toggle();
    }    
});

$("a.edit-delivery").click(function(){
    if ($("#delivery-frm").css("display") == "none"){
        $("#collapseThree").addClass("show");
        $("#delivery-frm").show("slow");
        $("#delivery-worked").hide("slow");
        $("#delivery-cancel").toggle();
    }    
});

$("a.cancel-delivery").click(function(){
    if ($("#delivery-worked").css("display") == "none"){
        $("#delivery-worked").show("slow");
        $("#delivery-frm").hide("slow");
        $("#delivery-cancel").toggle();
    }    
});

function eidt_item_size(itemId){
    $.ajax({
        url :  $('#siz-url-'+itemId).val(),
        type : 'GET',
        dataType:'json',
        success : function(data) {
        url :  $('#siz-url-'+itemId).val(),
            traySize =  $("#variantsizelist-"+itemId)
            console.log(data)
            traySize.find('option').remove().end();
            if(data !== null){
                jsonData =  JSON.parse(JSON.stringify(data));     
                $.each(jsonData, function(key,val){
                    size_id = val[0];
                    size_name = val[1];
                    size_desc = val[2];
                    console.log('size_id: '+ size_id + '   size_name : '+ size_name + ' size desc :'+size_desc );
                    traySize.append($('<option></option>').val(size_id).text(size_name));
                    traySize.niceSelect('update');
                })
                if ($("#size-update-"+itemId).css("display") == "none"){
                    $("#size-update-"+itemId).show();
                }
            }    
        },
        error : function(request,error)
        {
            $("#size-update-"+itemId).hide();
            $('#error-display-'+itemId).innerHTML("No sizes available for this product")
        }
    });    
}



function toggel_eidt_size(itemId){
    if ($("#size-update-"+itemId).css("display") == "block"){
        $("#size-update-"+itemId).hide();
    }    
}

