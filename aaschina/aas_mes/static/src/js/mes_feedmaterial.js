/**
 * Created by luforn on 2018-4-13.
 */

$(function(){

    var scanable = true; //是否可以继续扫描
    new VScanner(function(barcode) {
        if (barcode == null || barcode == '') {
            scanable = true;
            layer.msg('扫描条码异常！', {icon: 5});
            return;
        }
        action_feeding_scan(barcode);
    });

    function action_feeding_scan(barcode){
        var meslineid = parseInt($('#currentline').attr('meslineid'));
        if (meslineid==0){
            layer.msg('当前还未设置产线信息，请设置需要上料的产线！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode, 'meslineid': meslineid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/feedmaterial/scaning',
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
                var material = dresult.material;
                var temptr = $('<tr class="aas-material"></tr>').prependTo($('#feedmaterialist'));
                temptr.attr('barcode', material.barcode);
                $('<td></td>').html(material.label_name).appendTo(temptr);
                $('<td></td>').html(material.container_name).appendTo(temptr);
                $('<td></td>').html(material.material_code).appendTo(temptr);
                $('<td></td>').html(material.material_lot).appendTo(temptr);
                $('<td></td>').html(material.material_qty).appendTo(temptr);
                var operatetd = $('<td style="cursor:pointer;"></td>').appendTo(temptr);
                $('<span class="label label-danger pull-right aasdel"></span>').html('删除').appendTo(operatetd).click(function(){
                    var temptr = $(this).parent().parent();
                    action_delmaterial(temptr);
                });
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //切换产线
    $('li.aas-mesline').click(function(){
        var materialist = $('.aas-material');
        if (materialist!=undefined && materialist!=null && materialist.length>0){
            layer.msg('当前还有已扫描未提交的信息，请先处理已扫描的记录再切换产线！', {icon: 5});
            return ;
        }
        var meslineid = $(this).attr('meslineid');
        var meslinename = $(this).attr('meslinename');
        $('#currentline').attr('meslineid', meslineid);
        $('#currentline').val(meslinename);
    });

    //删除扫描记录
    $('span.aasdel').click(function(){
        var temptr = $(this).parent().parent();
        action_delmaterial(temptr);
    });

    function action_delmaterial(temptr){
        layer.confirm('您确认删除当前记录信息！', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            temptr.remove();
        },function(){});
    }

    //提交上料信息
    $('#action_dofeeding').click(function(){
        var doing = parseInt($('#action_dofeeding').attr('doing'));
        if(doing==1){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        var materialist = $('.aas-material');
        if (materialist==undefined || materialist==null || materialist.length<=0){
            $('#action_dofeeding').attr('doing', '0');
            layer.msg('当前还没有扫描上料记录！', {icon: 5});
            return ;
        }
        var meslineid = parseInt($('#currentline').attr('meslineid'));
        if (meslineid==0){
            $('#action_dofeeding').attr('doing', '0');
            layer.msg('当前还未设置产线信息，请设置需要上料的产线！', {icon: 5});
            return ;
        }
        var barcodes = [];
        $.each(materialist, function(index, temptr){
            barcodes.push($(temptr).attr('barcode'));
        });
        $('#action_dofeeding').attr('doing', '1');
        var doparams = {'barcodes': barcodes, 'meslineid': meslineid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var doneindex = layer.load(0, {shade: [0.2,'#000000']});
        $.ajax({
            url: '/aasmes/feedmaterial/dofeeding',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:60000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: doparams, id: access_id}),
            success:function(data){
                layer.close(doneindex);
                $('#action_dofeeding').attr('doing', '0');
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#feedmaterialist').html('');
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                layer.close(doneindex);
                $('#action_dofeeding').attr('doing', '0');
            }
        });



    });


});
