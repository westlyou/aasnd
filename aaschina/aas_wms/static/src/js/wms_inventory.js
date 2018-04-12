/**
 * Created by luforn on 2018-4-12.
 */

$(function(){

    var scanable = true;

    new VScanner(function(barcode){
        if(barcode==null || barcode==''){
            layer.msg('扫描条码异常！', {icon: 5});
            return ;
        }
        action_scaning(barcode);
    });

    function action_scaning(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var inventoryid = parseInt($('#ainventory').attr('inventoryid'));
        var scanparams = {'barcode': barcode, 'inventoryid': inventoryid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aaswms/inventory/scaning',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                scanable = true;
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var ilabel = dresult.ilabel;
                var temptr = $('<tr></tr>').attr('id', 'ilist_'+ilabel.list_id).prependTo($('#ainventorylist'));
                $('<td></td>').html(ilabel.product_code).appendTo(temptr);
                $('<td></td>').html(ilabel.product_lot).appendTo(temptr);
                $('<td></td>').html(ilabel.product_qty).appendTo(temptr);
                $('<td></td>').html(ilabel.location_name).appendTo(temptr);
                $('<td></td>').html(ilabel.label_name).appendTo(temptr);
                $('<td></td>').html(ilabel.container_name).appendTo(temptr);
                var operatetd = $('<td style="cursor:pointer;"></td>').appendTo(temptr);
                $('<span class="label label-danger pull-right aas-inventory"></span>')
                    .attr('listid', ilabel.list_id).html('删除').appendTo(operatetd);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }


    //删除错误扫描
    $('#ainventorylist').on('click', 'span.label-danger', function(){
        var listid = parseInt($(this).attr('listid'));
        layer.confirm('您确认要删除当前扫描记录？', {'btn': ['确定', '取消']}, function(index) {
            layer.close(index);
            delilabel(listid);
        });
    });

    function delilabel(listid){
        var params = {'ilabelid': listid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aaswms/inventory/scandel',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var temptr = $('#ilist_'+listid);
                if(temptr!=undefined && temptr.length>0){
                    temptr.remove();
                }
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
            }
        });
    }

    //返回盘点单
    $('#action_comeback').click(function(){
        window.history.go(-1);
    });


});
