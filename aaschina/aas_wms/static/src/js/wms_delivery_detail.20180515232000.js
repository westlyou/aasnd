/**
 * Created by luforn on 2018-5-15.
 */

$(function(){

    $('#barcodeipt').focus();

    var nativeSpeech = new SpeechSynthesisUtterance();
    nativeSpeech.lang = 'zh';
    nativeSpeech.rate = 1.2;
    nativeSpeech.pitch = 1.5;

    function nativespeak(message){
        nativeSpeech.text = message;
        speechSynthesis.speak(nativeSpeech);
    }

    //删除扫描记录
    $('a.labeldel').click(function(){
        var self = $(this);
        layer.confirm('您确认要删除拣货记录？', {'btn': ['确认', '取消']}, function(index){
            layer.close(index);
            action_dellabel(self);
        }, function(){
            $('#barcodeipt').val('').focus();
        });
    });

    function action_dellabel(operationtd){
        var operationid = parseInt(operationtd.attr('operationid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var params = {'operationid': operationid};
        $.ajax({
            url: '/aaswms/delivery/deloperation',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:30000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id}),
            success:function(data){
                $('#barcodeipt').val('').focus();
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    $('#barcodeipt').val('').focus();
                    return ;
                }
                operationtd.parent().parent().remove();
                var temproduct = $('#product-'+dresult.product_id);
                temproduct.attr('pickingqty', dresult.picking_qty).html(dresult.picking_qty);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                $('#barcodeipt').val('').focus();
            }
        });
    }


    // 条码扫描
    $('#barcodeipt').keyup(function(event){
        event.stopPropagation();
        if(event.which==13){
            var barcode = $(this).val();
            if(barcode==undefined || barcode==null || barcode==''){
                layer.msg('请确认您扫描了一个有效标签！', {icon: 5});
                $('#barcodeipt').val('').focus();
                return ;
            }
            var prefix = barcode.substring(0,2);
            if(prefix!='AC'){
                layer.msg('扫描异常，请确认是否扫描有效的发货标签！', {icon: 5});
                $('#barcodeipt').val('').focus();
                return ;
            }
            action_scanlabel(barcode);
        }
    });

    function action_scanlabel(barcode){
        var deliveryid = parseInt($('#cdelivery').attr('deliveryid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var params = {'deliveryid': deliveryid, 'barcode': barcode};
        $.ajax({
            url: '/aaswms/delivery/scanlabel',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id}),
            success:function(data){
                $('#barcodeipt').val('').focus();
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    $('#barcodeipt').val('').focus();
                    nativespeak(dresult.message);
                    return ;
                }

                var temproduct = $('#product-'+dresult.product_id);
                temproduct.attr('pickingqty', dresult.picking_qty).html(dresult.picking_qty);
                var tlabel = dresult.label;
                nativespeak('扫描'+tlabel.product_qty);
                var temptr = $('<tr></tr>').prependTo($('#operationlist'));
                $('<td></td>').html(tlabel.label_name).appendTo(temptr);
                $('<td></td>').html(tlabel.product_code).appendTo(temptr);
                $('<td></td>').html(tlabel.product_lot).appendTo(temptr);
                $('<td></td>').html(tlabel.product_qty).appendTo(temptr);
                $('<td></td>').html(tlabel.location_name).appendTo(temptr);
                var opttd = $('<td></td>').appendTo(temptr);
                var operationa = $('<a href="javascript:void(0);" class="labeldel" style="cursor:pointer;"></a>').appendTo(opttd);
                operationa.attr('operationid', tlabel.operation_id);
                operationa.html('<span class="label label-danger">删除</span>').click(function(){
                    action_dellabel(operationa);
                });
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                $('#barcodeipt').val('').focus();
            }
        });
    }


    //执行发货
    $('#actiondone').click(function(){
        layer.confirm('您确认要执行发货吗？', {'btn': ['确认', '取消']}, function(index){
            layer.close(index);
            action_done();
        }, function(){
            $('#barcodeipt').val('').focus();
        });
    });


    function action_done(){
        if(parseInt($('#actiondone').attr('doing'))==1){
            nativespeak('操作正在处理，请耐心等待');
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            $('#barcodeipt').val('').focus();
        }
        var deliveryid = parseInt($('#cdelivery').attr('deliveryid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var params = {'deliveryid': deliveryid};
        $('#actiondone').attr('doing', '1');
        $.ajax({
            url: '/aaswms/delivery/dodelivery',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id}),
            success:function(data){
                $('#actiondone').attr('doing', '0');
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    $('#barcodeipt').val('').focus();
                    nativespeak(dresult.message);
                    return ;
                }
                nativespeak('发货执行成功，即将返回主页');
                window.location.replace('/aaswms/delivery');
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                $('#actiondone').attr('doing', '0');
                $('#barcodeipt').val('').focus();
            }
        });
    }

    //返回主页
    $('#actionback').click(function(){
        layer.confirm('您确认要返回到主页面吗？', {'btn': ['确认', '取消']}, function(index){
            layer.close(index);
            window.location.replace('/aaswms/delivery');
        }, function(){
            $('#barcodeipt').val('').focus();
        });
    });


});
