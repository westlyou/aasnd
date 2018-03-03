/**
 * Created by luforn on 2017-11-3.
 */

$(function(){

    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    $('#mes_barcode').focus();

    // 条码扫描
    $('#mes_barcode').keyup(function(event){
        event.stopPropagation();
        if(event.which==13){
            var barcode = $(this).val();
            if(barcode==undefined || barcode==null || barcode==''){
                layer.msg('请先扫描相关条码！', {icon: 5});
                return ;
            }
            var prefix = barcode.substring(0,2);
            if(prefix=='AM'){
                action_scanemployee(barcode);
            }else if(prefix=='AC'){
                action_scanmaterial(barcode);
            }else if(prefix=='AU'){
                action_scanwireorder(barcode);
            }else if(prefix=='AT'){
                action_scancontainer(barcode);
            }else if(prefix=='AK'){
                action_scanequipment(barcode);
            }else{
                layer.msg('扫描异常，请确认是否在上岗扫描、上料扫描、容器扫描、设备扫描或者工单扫描！', {icon: 5});
                $('#mes_barcode').val('').focus();
                return ;
            }
            $('#mes_barcode').val('').focus();
        }
    });



    //扫描员工卡
    function action_scanemployee(barcode){
        var equipmentid = parseInt($('#mes_equipment').attr('equipmentid'));
        if(equipmentid==0){
            layer.msg('请先扫描设备二维码，添加设备后再上岗扫描！', {icon: 5});
            return ;
        }
        var scanparams = {'barcode': barcode, 'equipment_id': equipmentid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/scanemployee',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.message!='' && dresult.message!=null){
                    layer.msg(dresult.message, {icon: 1});
                }
                if(dresult.action=='working'){
                    $('#mes_employee').attr('employeeid', dresult.employee_id).html(dresult.employee_name);
                }else{
                    $('#mes_employee').attr('employeeid', '0').html('');
                    action_leave(dresult.attendance_id);
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //扫描设备
    function action_scanequipment(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/scanequipment',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_equipment').attr('equipmentid', dresult.equipment_id).html(dresult.equipment_code);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //扫描线材工单
    function action_scanwireorder(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/scanwireorder',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.wireorder_id == $('#mes_wireorder').attr('wireorderid')){
                    layer.msg('线材工单已经扫描过，请不要重复操作！', {icon: 5});
                    return ;
                }
                $('#mes_wireorder').attr('wireorderid', dresult.wireorder_id).html(dresult.wireorder_name);
                $('#mes_product').html(dresult.product_code);
                $('#mes_pqty').html(dresult.product_qty);
                $('#workorderlist').html('');
                $.each(dresult.workorderlist, function(index, workorder){
                    var workorder_id = 'workorder_'+workorder.id;
                    var ordertr = $('<tr class="workorder"></tr>').attr({
                        'id': workorder_id, 'output_qty': workorder.output_qty,
                        'workorderid': workorder.id, 'order_name': workorder.order_name, 'product_code': workorder.product_code
                    });
                    $('<td></td>').appendTo(ordertr).html('<input type="checkbox"/>');
                    $('<td></td>').appendTo(ordertr).html(workorder.order_name);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_code);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_uom);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_qty);
                    $('<td></td>').appendTo(ordertr).html(workorder.output_qty);
                    $('<td></td>').appendTo(ordertr).html(workorder.scrap_qty);
                    $('<td></td>').appendTo(ordertr).html(workorder.state_name);
                    $('#workorderlist').append(ordertr);
                    ordertr.click(function(){
                        temptrclick(ordertr);
                    });
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //上料扫描
    function action_scanmaterial(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/scanmaterial',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var materialstr = '<a href="javascript:void(0);">'+dresult.material_name+'<span class="pull-right">' +
                    dresult.material_qty+'</span></a>';
                $('<li></li>').html(materialstr).prependTo($('#wirecut_materiallist'));
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //扫描容器
    function action_scancontainer(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/scancontainer',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 10000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_container').attr('containerid', dresult.container_id).html(dresult.container_name);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //产出
    $('#wire_output').click(function(){
        var equipment_id = parseInt($('#mes_equipment').attr('equipmentid'));
        if(equipment_id==0){
            layer.msg('当前工位还未添加设备，请先扫描设备二维码添加设备！', {icon: 5});
            return ;
        }
        var employee_id = parseInt($('#mes_employee').attr('employeeid'));
        if(employee_id==0){
            layer.msg('当前工位还没有员工上岗，请先扫描员工卡上岗！', {icon: 5});
            return ;
        }
        var containerid = parseInt($('#mes_container').attr('containerid'));
        if(containerid==0){
            layer.msg('您还没添加产出容器，请先扫描容器标签添加容器！', {icon: 5});
            return ;
        }
        var wireorderid = parseInt($('#mes_wireorder').attr('wireorderid'));
        if(wireorderid==0){
            layer.msg('您还未扫描线材工单！', {icon: 5});
            return ;
        }
        var workorderid = parseInt($('#mes_workorder').attr('workorderid'));
        if (workorderid==0){
            layer.msg('您还没选择需要产出的线材，请先选择需要产出的线材！', {icon: 5});
            return ;
        }
        layer.prompt({'title': '输入需要产出数量，并确认', 'formType': 3, 'value': 200}, function(text, index){
            if(!isAboveZeroFloat(text)){
                layer.msg('产出数量必须是一个大于零的整数！', {icon: 5});
                return ;
            }
            layer.close(index);
            var output_qty = parseFloat(text);
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var outputparams = {'workorder_id': workorderid, 'output_qty': output_qty, 'container_id': containerid};
            outputparams['employee_id'] = employee_id;
            outputparams['equipment_id'] = equipment_id;
            $.ajax({
                url: '/aasmes/wirecutting/output',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: outputparams, id: access_id}),
                success:function(data){
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    action_refresh_cutting(wireorderid, workorderid);
                },
                error:function(xhr,type,errorThrown){ console.log(type);}
            });
        });
    });

    //线材报废
    $('#wire_scrap').click(function(){
        //layer.confirm('您确认是要线材报废？', {'btn': ['确定', '取消']}, function(){ action_scrap(); }, function(){});
        action_scrap();
    });
    //报废
    function action_scrap(){
        var equipment_id = parseInt($('#mes_equipment').attr('equipmentid'));
        if(equipment_id==0){
            layer.msg('当前工位还未添加设备，请先扫描设备二维码添加设备！', {icon: 5});
            return ;
        }
        var employee_id = parseInt($('#mes_employee').attr('employeeid'));
        if(employee_id==0){
            layer.msg('当前工位还没有员工上岗，请先扫描员工卡上岗！', {icon: 5});
            return ;
        }
        var wireorderid = parseInt($('#mes_wireorder').attr('wireorderid'));
        if(wireorderid==0){
            layer.msg('您还未扫描线材工单！', {icon: 5});
            return ;
        }
        var workorderid = parseInt($('#mes_workorder').attr('workorderid'));
        if (workorderid==0){
            layer.msg('您还没选择需要报废的线材，请先选择需要报废的线材！', {icon: 5});
            return ;
        }
        layer.prompt({title: '输入需要报废数量，并确认', formType: 3}, function(text, index){
            if(!isAboveZeroFloat(text)){
                layer.msg('报废数量必须是一个大于零的正数！', {icon: 5});
                return ;
            }
            layer.close(index);
            var scrap_qty = parseFloat(text);
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var scrapparams = {'workorder_id': workorderid, 'scrap_qty': scrap_qty};
            scrapparams['employee_id'] = employee_id;
            scrapparams['equipment_id'] = equipment_id;
            $.ajax({
                url: '/aasmes/wirecutting/scrap',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scrapparams, id: access_id}),
                success:function(data){
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    action_refresh_cutting(wireorderid, workorderid);
                },
                error:function(xhr,type,errorThrown){ console.log(type);}
            });
        });
    }

    //切换生产子工单
    function temptrclick(datatr){
        var self = $(datatr);
        if(self.hasClass('cutting')){
            var tempipt = self.children(":first").children(":first");
            tempipt.removeAttr('checked');
            self.removeClass('cutting');
            $('#mes_workorder').attr('workorderid', '0').html('');
        }else{
            var cuttingtrs = $('.cutting');
            if(cuttingtrs!=undefined && cuttingtrs!=null && cuttingtrs.length>0){
                $.each(cuttingtrs, function(index, ctr){
                    var tempipt = $(ctr).children(":first").children(":first");
                    tempipt.removeAttr('checked');
                    $(ctr).removeClass('cutting');
                });
            }
            var selfipt = self.children(":first").children(":first");
            selfipt.attr('checked','checked');
            self.addClass('cutting');
            var workorder_id = self.attr('workorderid');
            var product_code = self.attr('product_code');
            $('#mes_workorder').attr('workorderid', workorder_id).html(product_code);
        }
    }

    //刷新页面
    $('#wire_refresh').click(function(){
        var wireorderid = parseInt($('#mes_wireorder').attr('wireorderid'));
        var workorderid = parseInt($('#mes_workorder').attr('workorderid'));
        if(wireorderid==0){
            window.location.reload(true);
        }else{
            action_refresh_cutting(wireorderid, workorderid);
        }
    });

    function action_refresh_cutting(wireorderid, workorderid){
        var refreshparams = {'wireorder_id': wireorderid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/actionrefresh',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: refreshparams, id: access_id}),
            success:function(data){
                $('#mes_wireorder').attr('wireorderid', '0').html('');
                $('#mes_product').html('');
                $('#mes_pqty').html('');
                $('#workorderlist').html('');
                $('#mes_workorder').attr('workorderid', '0').html('');
                $('#mes_mesline').html('');
                $('#mes_workstation').html('');
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_wireorder').attr('wireorderid', dresult.wireorder_id).html(dresult.wireorder_name);
                $('#mes_product').html(dresult.product_code);
                $('#mes_pqty').html(dresult.product_qty);
                $('#mes_mesline').html(dresult.mesline_name);
                $('#mes_workstation').html(dresult.workstation_name);
                $.each(dresult.workorderlist, function(index, workorder){
                    var workorder_id = 'workorder_'+workorder.id;
                    var ordertr = $('<tr class="workorder"></tr>').attr({
                        'id': workorder_id, 'output_qty': workorder.output_qty,
                        'workorderid': workorder.id, 'order_name': workorder.order_name, 'product_code': workorder.product_code
                    });
                    $('<td></td>').appendTo(ordertr).html('<input type="checkbox"/>');
                    $('<td></td>').appendTo(ordertr).html(workorder.order_name);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_code);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_uom);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_qty);
                    $('<td></td>').appendTo(ordertr).html(workorder.output_qty);
                    $('<td></td>').appendTo(ordertr).html(workorder.scrap_qty);
                    $('<td></td>').appendTo(ordertr).html(workorder.state_name);
                    $('#workorderlist').append(ordertr);
                    ordertr.click(function(){
                        temptrclick(ordertr);
                    });
                });
                $('#wirecut_materiallist').html('');
                if(dresult.materiallist.length > 0){
                    var wmateriallist = $('#wirecut_materiallist');
                    $.each(dresult.materiallist, function(index, tmaterial){
                        var materialstr = '<a href="javascript:void(0);">'+tmaterial.material_name +
                            '<span class="pull-right">'+tmaterial.material_qty+'</span></a>';
                        $('<li></li>').html(materialstr).appendTo(wmateriallist);
                    });
                }
                if(workorderid > 0){
                    $('#workorder_'+workorderid).click();
                }
                $('#mes_container').attr('containerid', '0').html('');
                $('#mes_barcode').val('').focus();
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    function action_leave(attendanceid){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/attendance/loadingleavelist',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {}, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.leavelist.length > 0){
                    initleavelisthtml(attendanceid, dresult.leavelist);
                }else{
                    layer.msg('您已离岗！', {icon: 1});
                }
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
            }
        });
    }

    function initleavelisthtml(attendanceid, leavelist){
        var tcontent = '<div class="row" style="margin-top: 10px;clear: both;zoom: 1; padding:0px 20px;">';
        $.each(leavelist, function(index, tleave){
            tcontent += '<div class="col-md-4">';
            tcontent += '<a href="javascript:void(0);" class="btn btn-block btn-success aas-leave" ';
            tcontent += 'style="margin-top:10px;margin-bottom:10px; height:100px; line-height:100px; font-size:25px; padding:0;" ';
            tcontent += 'leaveid='+tleave.leave_id+'>'+tleave.leave_name+'</a>';
            tcontent += '</div>';
        });
        tcontent += '</div>';
        var lindex = layer.open({
            type: 1,
            closeBtn: 0,
            skin: 'layui-layer-rim',
            title: '请在下面选择您的离岗原因',
            area: ['980px', '560px'],
            content: tcontent
        });
        $('.aas-leave').click(function(){
            var self = $(this);
            var leaveid = parseInt(self.attr('leaveid'));
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var lparams = {'attendanceid': attendanceid, 'leaveid': leaveid};
            $.ajax({
                url: '/aasmes/attendance/actionleave',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: lparams, id: access_id}),
                success:function(data){
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    layer.close(lindex);
                },
                error:function(xhr,type,errorThrown){ console.log(type); }
            });

        });
    }

    /*function action_producttest(testtype){

    }

    //首件检测
    $('#action_test_firstone').click(function(){
        action_producttest('firstone');
    });

    //末件检测
    $('#action_test_lastone').click(function(){
        action_producttest('lastone');
    });

    //抽样检测
    $('#action_test_random').click(function(){
        action_producttest('random');
    });*/

});
