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
                var allocationtr = $('<tr></tr>').prependTo($('#allocationlist'));
                $('<td></td>').html(dresult.product_code).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_uom).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_lot).appendTo(allocationtr);
                $('<td></td>').html(dresult.product_qty).appendTo(allocationtr);
                $('<td></td>').html(dresult.label_name).appendTo(allocationtr);
                $('<td></td>').html('').appendTo(allocationtr);
                var labelids = $('#mes_label').attr('labelids');
                if(labelids==null||labelids==""){
                    labelids = dresult.label_id.toString();
                }else{
                    labelids += ',' + dresult.label_id;
                }
                $('#mes_label').attr('labelids', labelids).html(dresult.label_name);
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
                $.each(dresult.productlines, function(index, record){
                    var allocationtr = $('<tr></tr>').prependTo($('#allocationlist'));
                    $('<td></td>').html(record.product_code).appendTo(allocationtr);
                    $('<td></td>').html(record.product_uom).appendTo(allocationtr);
                    $('<td></td>').html(record.product_lot).appendTo(allocationtr);
                    $('<td></td>').html(record.product_qty).appendTo(allocationtr);
                    $('<td></td>').html('').appendTo(allocationtr);
                    $('<td></td>').html(record.container_name).appendTo(allocationtr);
                });
                var containerids = $('#mes_container').attr('containerids');
                if(containerids==null || containerids==''){
                    containerids = dresult.container_id.toString();
                }else{
                    containerids += ',' + dresult.container_id;
                }
                $('#mes_container').attr('containerids', containerids).html(dresult.container_name);
                $('#mes_label').html('');
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }


    $('#action_done').click(function(){
        var containerids = $('#mes_container').attr('containerids');
        var labelids = $('#mes_label').attr('labelids');
        if((containerids==null || containerids=='') && (labelids==null || labelids=='')){
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
        var containeridlist = [];
        if(containerids!=null && containerids!=""){
            $.each(containerids.split(','), function(index, containerid){
                containeridlist.push(parseInt(containerid));
            });
        }
        var labelidlist = []
        if(labelids!=null && labelids!=""){
            $.each(labelids.split(','), function(index, labelid){
                labelidlist.push(parseInt(labelid));
            });
        }
        layer.confirm('您确认要执行调拨？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            action_doallocate(meslineid, employeeid, containeridlist, labelidlist);
        }, function(){});
    });


    function action_doallocate(meslineid, operatorid, containerids, labelids){
        var doparams = {'meslineid': meslineid, 'operatorid': operatorid};
        if(containerids.length > 0){
            doparams['containerids'] = containerids;
        }
        if(labelids.length > 0){
            doparams['labelids'] = labelids;
        }
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/allocation/doallocate',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: doparams, id: access_id}),
            success:function(data){
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
            }
        });
    }

    //单击产线行
    $('#mesline_list').on('click', 'li.mesline', function(){
        var self = $(this);
        $('#mes_mesline').attr('meslineid', self.attr('meslineid')).html(self.attr('meslinename'));
    });

});
