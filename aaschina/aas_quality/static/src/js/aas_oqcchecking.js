/**
 * Created by luforn on 2018-3-5.
 */

$(function(){

    new VScanner(function(barcode){
        if(barcode==null || barcode==''){
            layer.msg('扫描条码异常！', {icon: 5});
            return ;
        }
        action_scan_label(barcode);
    });

    //扫描标签
    function action_scan_label(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasquality/oqcchecking/scanlabel',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var labeltr = $('#label_'+dresult.label_id);
                if(labeltr!=null && labeltr.length > 0){
                    layer.msg('标签已存在，请不要重复扫描！', {icon: 5});
                    return ;
                }
                var pid = $('#quality_product').attr('pid');
                if(pid==0 || pid== '0'){
                    $('#quality_product').attr('pid', dresult.product_id).html(dresult.product_code);
                    $('#quality_customerpn').html(dresult.customer_pn);
                }else{
                    var tempid = parseInt(pid);
                    if(tempid!=dresult.product_id){
                        layer.msg('标签异常，当前标签可能和其他待报检标签上产品不同！', {icon: 5});
                        return ;
                    }
                }
                var quality_qty = parseFloat($('#quality_qty').attr('pqty'));
                quality_qty += dresult.product_qty;
                $('#quality_qty').attr('pqty', quality_qty).html(quality_qty);
                var quality_count = parseInt($('#quality_count').attr('count'));
                quality_count += 1;
                $('#quality_count').attr('count', quality_count).html(quality_count);
                $('#quality_label').html(dresult.label_name);
                var temptr = $('<tr class="aas-label"></tr>').prependTo($('#tochecklabellist'));
                temptr.attr({'id': 'label_'+dresult.label_id, 'labelid': dresult.label_id});
                $('<td></td>').html(dresult.label_name).appendTo(temptr);
                $('<td></td>').html(dresult.product_code).appendTo(temptr);
                $('<td></td>').html(dresult.product_lot).appendTo(temptr);
                $('<td></td>').html(dresult.product_qty).appendTo(temptr);
                var operationcol = $('<td></td>').appendTo(temptr);
                $('<span class="label label-danger">删除</span>').attr({
                    'labelid': dresult.label_id, 'pqty': dresult.product_qty
                }).appendTo(operationcol).click(function(){
                    var tempqty = parseFloat($('#quality_qty').attr('pqty')) - dresult.product_qty;
                    $('#quality_qty').attr('pqty', tempqty).html(tempqty);
                    var tempcount = parseInt($('#quality_count').attr('count')) - 1;
                    $('#quality_count').attr('count', tempcount).html(tempcount);
                    temptr.remove();
                    $('#quality_label').html('');
                    var templist = $('.aas-label');
                    if(templist==undefined || templist==null ||templist.length==0){
                        $('#quality_product').attr('pid', '0').html('');
                        $('#quality_customerpn').html('');
                        $('#quality_qty').attr('pqty', tempqty).html('');
                        $('#quality_count').attr('count', tempcount).html('');
                    }
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }


    //提交报检
    $('#action_commit').click(function(){
        var labelist = $('.aas-label');
        if(labelist==undefined || labelist==null || labelist.length<=0){
            layer.msg('请确认是否已经扫描待检测的标签！', {icon: 5});
            return ;
        }
        var labelids = [];
        $.each(labelist, function(index, labeline){
            labelids.push(parseInt($(labeline).attr('labelid')));
        });
        var temparams = {'labelids': labelids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasquality/oqcchecking/docommit',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                layer.msg('报检信息已提交，请耐心等待！', {icon: 5});
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });


});
