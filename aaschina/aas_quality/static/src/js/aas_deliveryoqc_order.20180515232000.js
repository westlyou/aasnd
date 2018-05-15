/**
 * Created by luforn on 2018-3-5.
 * Update by luforn on 2018-5-15.
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


    // 条码扫描
    $('#barcodeipt').keyup(function(event){
        event.stopPropagation();
        if(event.which==13){
            var barcode = $(this).val();
            if(barcode==undefined || barcode==null || barcode==''){
                layer.msg('请先扫描相关条码！', {icon: 5});
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


    //扫描标签
    function action_scanlabel(barcode){
        var deliveryid = parseInt($('#cdelivery').attr('deliveryid'));
        var scanparams = {'barcode': barcode, 'deliveryid': deliveryid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasquality/deliveryoqc/scanlabel',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                $('#barcodeipt').val('').focus();
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    $('#barcodeipt').val('').focus();
                    nativespeak(dresult.message);
                    return ;
                }
                var temptr = $('#label'+dresult.label_id);
                if(temptr!=undefined && temptr!=null && temptr.length > 0){
                    nativespeak('标签已存在，请不要重复扫描');
                    layer.msg('标签已存在，请不要重复扫描', {icon: 5});
                    $('#barcodeipt').val('').focus();
                    return ;
                }
                var temproduct = $('#product-'+dresult.product_id);
                if(temproduct==undefined || temproduct==null || temproduct.length <= 0){
                    $('#barcodeipt').val('').focus();
                    return ;
                }
                var current_qty = dresult.product_qty;
                var picking_qty = parseFloat(temproduct.attr('pickingqty')) + current_qty;
                temproduct.attr('pickingqty', picking_qty).html(picking_qty);
                var pickingitem = $('<tr class="oqclabel"></tr>').prependTo($('#operationlist'));
                pickingitem.attr('labelid', dresult.label_id);
                $('<td></td>').html(dresult.label_name).appendTo(pickingitem);
                $('<td></td>').html(dresult.product_code).appendTo(pickingitem);
                $('<td></td>').html(dresult.product_lot).appendTo(pickingitem);
                $('<td></td>').html(dresult.product_qty).appendTo(pickingitem);
                $('<td></td>').html(dresult.location_name).appendTo(pickingitem);
                var operationtd = $('<td></td>').appendTo(pickingitem);
                var operationa = $('<a href="javascript:void(0);" style="cursor:pointer;"></a>').appendTo(operationtd);
                operationa.html('<span class="label label-danger">删除</span>').click(function(){
                    var pickingqty = parseFloat(temproduct.attr('pickingqty')) - current_qty;
                    temproduct.attr('pickingqty', pickingqty).html(pickingqty);
                    pickingitem.remove();
                    $('#barcodeipt').val('').focus();
                });
                nativespeak('扫描'+current_qty);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
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

    //重新计算拣货清单
    $('#actionrepicking').click(function(){
        var self = $(this);
        if (parseInt(self.attr('doing')) == 1){
            nativespeak('操作正在处理，请耐心等待');
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            $('#barcodeipt').val('').focus();
            return ;
        }
        nativespeak('重新生成拣货清单，会清理已扫描记录，请确认是否重新生成');
        layer.confirm('您确认要重新计算拣货清单吗，拣货清单重新计算会清理已扫描记录？', {'btn': ['确认', '取消']}, function(index){
            layer.close(index);
            var deliveryid = parseInt($('#cdelivery').attr('deliveryid'));
            var temparams = {'deliveryid': deliveryid};
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            self.attr('doing', '1');
            $.ajax({
                url: '/aasquality/deliveryoqc/repicking',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
                success:function(data){
                    self.attr('doing', '0');
                    $('#barcodeipt').val('').focus();
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        $('#barcodeipt').val('').focus();
                        nativespeak(dresult.message);
                        return ;
                    }
                    window.location.reload(true);
                },
                error:function(xhr,type,errorThrown){
                    console.log(type);
                    self.attr('doing', '0');
                    $('#barcodeipt').val('').focus();
                }
            });
        }, function(){
            $('#barcodeipt').val('').focus();
        });
    });


    //提交报检
    $('#actiondocommit').click(function(){
        var self = $(this);
        if (parseInt(self.attr('doing')) == 1){
            nativespeak('操作正在处理，请耐心等待');
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            $('#barcodeipt').val('').focus();
            return ;
        }
        var labelist = $('.oqclabel');
        if(labelist==undefined || labelist==null || labelist.length<=0){
            nativespeak('请确认是否已经扫描待检测的标签');
            layer.msg('请确认是否已经扫描待检测的标签！', {icon: 5});
            $('#barcodeipt').val('').focus();
            return ;
        }
        var labelids = [];
        $.each(labelist, function(index, labeline){
            labelids.push(parseInt($(labeline).attr('labelid')));
        });
        var temparams = {'labelids': labelids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        self.attr('doing', '1');
        $.ajax({
            url: '/aasquality/deliveryoqc/docommit',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                $('#barcodeipt').val('').focus();
                self.attr('doing', '0');
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    $('#barcodeipt').val('').focus();
                    nativespeak(dresult.message);
                    return ;
                }
                nativespeak('OQC报检已提交，请通知OQC检测；即将返回主页');
                window.location.replace('/aaswms/delivery');
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                self.attr('doing', '0');
                $('#barcodeipt').val('').focus();
            }
        });
    });


});
