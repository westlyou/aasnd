/**
 * Created by luforn on 2017-11-20.
 */

$(function(){

    var scanable = true; //是否可以继续扫描
    new VScanner(function(barcode) {
        if (barcode == null || barcode == '') {
            scanable = true;
            layer.msg('扫描条码异常！', {icon: 5});
            return;
        }
        var prefix = barcode.substring(0,2);
        if(prefix=='AM'){
            action_scan_employee(barcode);
        }else if(prefix=='AC'){
            action_scan_label(barcode);
        }else if(prefix=='AT'){
            action_scan_container(barcode);
        }else{
            layer.msg('扫描条码异常,请确认您扫描的条码是否是一个有效的员工、容器或者标签条码', {icon: 5});
            return;
        }
    });

    //扫描员工卡
    function action_scan_employee(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/allocation/scanemployee',
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
                $('#mes_employee').attr('employeeid', dresult.employee_id);
                $('#mes_employee').html(dresult.employee_name);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //扫描标签
    function action_scan_label(barcode){
        var meslineid = parseInt($('#mes_mesline').attr('meslineid'));
        if(meslineid==0){
            layer.msg('请先选择目标产线！', {icon: 5});
            return ;
        }
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode, 'meslineid': meslineid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/allocation/scanlabel',
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
                var temptr = $('#label_'+dresult.label_id);
                if(temptr!=undefined && temptr!=null && temptr.length>0){
                    layer.msg('标签已存在，请不要重复扫描！', {icon: 5});
                    return ;
                }
                var allocationtr = $('<tr class="aas-label"></tr>').prependTo($('#allocationlist'));
                allocationtr.attr({'id': 'label_'+dresult.label_id, 'labelid': dresult.label_id});
                $('<td></td>').html(dresult.product_code).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_uom).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_lot).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_qty).appendTo(allocationtr);
                $('<td></td>').html(dresult.label_name).appendTo(allocationtr);
                $('<td></td>').html('').appendTo(allocationtr);
                var operationcol = $('<td></td>').appendTo(allocationtr);
                $('<span class="label label-danger">删除</span>').appendTo(operationcol).click(function(){
                    allocationtr.remove();
                    $('#mes_label').html('');
                    $('#mes_container').html('');
                });
                $('#mes_label').html(dresult.label_name);
                $('#mes_container').html('');
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //扫描容器
    function action_scan_container(barcode){
        var meslineid = parseInt($('#mes_mesline').attr('meslineid'));
        if(meslineid==0){
            layer.msg('请先选择目标产线！', {icon: 5});
            return ;
        }
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode, 'meslineid': meslineid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/allocation/scancontainer',
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
                var temptr = $('#container_'+dresult.container_id);
                if(temptr!=undefined && temptr!=null && temptr.length>0){
                    layer.msg('容器已存在请不要重复扫描！', {icon: 5});
                    return ;
                }
                var allocationtr = $('<tr class="aas-container"></tr>').prependTo($('#allocationlist'));
                allocationtr.attr({'id': 'container_'+dresult.container_id, 'containerid': dresult.container_id});
                $('<td></td>').html(dresult.product_code).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_uom).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_lot).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_qty).appendTo(allocationtr);
                $('<td></td>').html('').appendTo(allocationtr);
                $('<td></td>').html(dresult.container_name).appendTo(allocationtr);
                var operationcol = $('<td></td>').appendTo(allocationtr);
                $('<span class="label label-danger">删除</span>').appendTo(operationcol).click(function(){
                    allocationtr.remove();
                    $('#mes_label').html('');
                    $('#mes_container').html('');
                });
                $('#mes_label').html('');
                $('#mes_container').html(dresult.container_name);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }


    $('#action_done').click(function(){
        var doing = parseInt($('#action_done').attr('doing'));
        if(doing==1){
            layer.msg('操作正在执行，请耐心等待！', {icon: 5});
            return ;
        }
        var labellist = $('.aas-label');
        var containerlist = $('.aas-container');
        var labelids = [];
        var containerids = [];
        if(labellist!=undefined && labellist!=null && labellist.length > 0){
            $.each(labellist, function(index, tlabel){
                var labelid = parseInt($(tlabel).attr('labelid'));
                labelids.push(labelid);
            });
        }
        if(containerlist!=undefined && containerlist!=null && containerlist.length > 0){
            $.each(containerlist, function(index, tcontainer){
                var containerid = parseInt($(tcontainer).attr('containerid'));
                containerids.push(containerid);
            });
        }
        if(labelids.length<=0 && containerids.length<=0){
            layer.msg('您还未添加调拨明细，暂时不可以确认调拨！', {icon: 5});
            return ;
        }
        var meslineid = parseInt($('#mes_mesline').attr('meslineid'));
        if(meslineid==0){
            layer.msg('请先选择目标产线！', {icon: 5});
            return ;
        }
        var employeeid = parseInt($('#mes_employee').attr('employeeid'));
        if(employeeid==0){
            layer.msg('请先选择扫描操作员工！', {icon: 5});
            return ;
        }
        layer.confirm('您确认要执行调拨？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            action_doallocate(meslineid, employeeid, containerids, labelids);
        }, function(){});
    });


    function action_doallocate(meslineid, operatorid, containerids, labelids){
        var doing = parseInt($('#action_done').attr('doing'));
        if(doing==1){
            layer.msg('操作正在执行，请耐心等待！', {icon: 5});
            return ;
        }
        var doparams = {'meslineid': meslineid, 'operatorid': operatorid};
        if(containerids.length > 0){
            doparams['containerids'] = containerids;
        }
        if(labelids.length > 0){
            doparams['labelids'] = labelids;
        }
        $('#action_done').attr('doing', '1');
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/allocation/doallocate',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:60000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: doparams, id: access_id}),
            success:function(data){
                $('#action_done').attr('doing', '0');
                scanable = true;
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_container').attr('containerids', '').html('');
                $('#mes_label').attr('labelids', '').html('');
                $('#allocationlist').html('');
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
                $('#action_done').attr('doing', '0');
            }
        });
    }

    //单击产线行
    $('#mesline_list').on('click', 'li.mesline', function(){
        var self = $(this);
        $('#mes_mesline').attr('meslineid', self.attr('meslineid')).html(self.attr('meslinename'));
    });

});
