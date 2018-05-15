/**
 * Created by luforn on 2017-11-30.
 */

$(function(){

    var nativeSpeech = new SpeechSynthesisUtterance();
    nativeSpeech.lang = 'zh';
    nativeSpeech.rate = 1.2;
    nativeSpeech.pitch = 1.5;

    function nativespeak(message){
        nativeSpeech.text = message;
        speechSynthesis.speak(nativeSpeech);
    }

    $('li.aas-delivery').click(function(){
        $('.aas-delivery').removeClass('active');
        $(this).addClass('active');
        var did = $(this).attr('did');
        var dname = $(this).attr('dname');
        $('#cdelivery').attr('deliveryid', did).html(dname);
    });

    //单击报检
    $('#actioninspection').click(function(){
        var deliveryid = $('#cdelivery').attr('deliveryid');
        if(parseInt(deliveryid) == 0){
            layer.msg('请先选择需要操作的发货单！', {icon: 5});
            nativespeak('请先选择需要操作的发货单');
            return ;
        }
        window.location.replace('/aasquality/deliveryoqc/'+deliveryid);
    });

    //单击发货
    $('#actiondeliver').click(function(){
        var deliveryid = $('#cdelivery').attr('deliveryid');
        if(parseInt(deliveryid) == 0){
            layer.msg('请先选择需要操作的发货单！', {icon: 5});
            nativespeak('请先选择需要操作的发货单');
            return ;
        }
        window.location.replace('/aaswms/delivery/detail/'+deliveryid);
    });

});
