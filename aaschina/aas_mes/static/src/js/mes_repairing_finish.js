/**
 * Created by luforn on 2018-6-4.
 */

$(function(){

    //初始化默认员工
    var repairerstr = localStorage.getItem('repairer');
    if(repairerstr!=null && repairerstr!=''){
        var repairer = JSON.parse(repairerstr);
        $('#mes_repairer').attr('employeeid', repairer.employee_id).val(repairer.employee_name);
    }

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
        }else{
            action_scan_serialnumber(barcode);
        }
    });

    function action_scan_employee(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/repairing/scanemployee',
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
                var empdata = {'employee_id': dresult.employee_id, 'employee_name': dresult.employee_name};
                localStorage.setItem('repairer', JSON.stringify(empdata));
                $('#mes_repairer').attr('employeeid', dresult.employee_id).val(dresult.employee_name);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    function action_scan_serialnumber(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/repairing/finish/scanserialnumber',
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
                $('#currentserial').attr('reworkid', dresult.rework_id).html(dresult.serialnumber_name);
                $('#mes_repairer').html(dresult.repairer_name);
                $('#repair_start').html(dresult.repair_time);
                $('#mes_badmode').html(dresult.badmode_name);
                $('#mes_commiter').html(dresult.commiter_name);
                $('#commit_time').html(dresult.commit_time);
                $('#mes_station').html(dresult.workstation_name);
                $('#mes_internalpn').html(dresult.internalpn);
                $('#mes_customerpn').html(dresult.customerpn);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    $('li.aas-mesline').click(function(){
        var self = this;
        var materialist = $('.aas-material');
        if(materialist!=undefined && materialist!=null && materialist.length>0){
            layer.confirm('您确认要返回维修主页面吗？', {'btn': ['确认', '取消']}, function(index) {
                layer.close(index);
                action_switch_mesline(self);
            });
        }else{
            action_switch_mesline(self);
        }
    });

    function action_switch_mesline(line){
        var meslineid = $(line).attr('meslineid');
        var meslinename = $(line).attr('meslinename');
        $('#mes_currentline').attr('meslineid', meslineid).val(meslinename);
        $('#materiallist').html('');
    }


    $('#action_repair_back').click(function(){
        layer.confirm('您确认要返回维修主页面吗？', {'btn': ['确认', '取消']}, function(index) {
            layer.close(index);
            window.location.replace('/aasmes/repairing');
        });
    });

    var doneflag = false;
    $('#action_repair_dofinish').click(function(){
        if(doneflag){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        var reworkid = parseInt($('#currentserial').attr('reworkid'));
        if(reworkid==0){
            doneflag = false;
            layer.msg('您还未扫描序列号，请先扫描需要维修报工的序列号！', {icon: 5});
            return ;
        }
        var commitmsg = '';
        var materiallist = $('tr.aas-material');
        if(materiallist==undefined || materiallist==null || materiallist.length<=0){
            commitmsg = '您还未添加材料消耗信息，您确认您的维修操作没有消耗材料吗？';
        }else{
            commitmsg = '您确认现在就提交维修操作信息吗？';
        }
        layer.confirm(commitmsg, {'btn': ['确认', '取消']}, function(index) {
            layer.close(index);
            dofinish(reworkid, materiallist);
        });
    });

    function dofinish(reworkid, materiallist){
        var temparams = {'reworkid': reworkid};
        if(materiallist!=undefined && materiallist!=null && materiallist.length>0){
            var materialines = [];
            var meslineid = parseInt($('#mes_currentline').attr('meslineid'));
            $.each(materiallist, function(index, material){
                materialines.push({
                    'mesline_id': meslineid,
                    'material_id': parseInt($(material).attr('materialid')),
                    'material_qty': parseFloat($(material).attr('materialqty'))
                })
            });
            temparams['materiallist'] = materialines;
        }
        doneflag = true;
        var doneindex = layer.load(0, {shade: [0.2,'#000000']});
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/repairing/finish/done',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:30000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                doneflag = false;
                layer.close(doneindex);
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){
                doneflag = false;
                console.log(type);
                layer.close(doneindex);
            }
        });
    }

    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    //添加消耗物料
    $('#action_addmaterial').click(function(){
        var reworkid = parseInt($('#currentserial').attr('reworkid'));
        if(reworkid==0){
            layer.msg('你还未扫描序列号，请先扫描序列号！', {icon: 5});
            return ;
        }
        var meslineid = parseInt($('#mes_currentline').attr('meslineid'));
        if(meslineid == 0){
            layer.msg('您还未设置用料产线，请先设置好用料产线！', {icon: 5});
            return ;
        }
        var layercontent = '<div class="form-group">';
        layercontent += '<div class="input-group" style="margin-top:40px;"> <div class="input-group-addon">原料</div>';
        layercontent += '<select id="mesmaterial" class="form-control select2" style="width: 100%;"></select></div>';
        layercontent += '<div class="input-group" style="margin-top:40px;"> <div class="input-group-addon">数量</div>';
        layercontent += '<input id="materialqty" type="text" class="form-control pull-right"/></div>';
        layercontent += '<div class="row" style="margin-top:60px;padding-left:20px;padding-right:20px;">';
        layercontent += '<div class="col-xs-4"><button id="materialcancel" type="button" class="btn btn-block btn-default">取消</button></div>';
        layercontent += '<div class="col-xs-4 col-xs-offset-4"><button id="materialconfirm" type="button" class="btn btn-block btn-primary">确定</button></div> </div>';
        layercontent += '</div>';
        var layerindex = layer.open({
            type: 1,
            title: '添加消耗物料',
            skin: 'layui-layer-molv',
            area: ['480px', '320px'], //宽高
            content: '<div style="padding:10px;">'+layercontent+'</div>'
        });
        $('.layui-layer-shade').css({'z-index': 9});
        $('.layui-layer-page').css({'z-index': 10});
        $('#mesmaterial').select2({
            placeholder: '选择待消耗原料编码...',
            ajax:{
                type: 'post', timeout:30000, dataType: 'json',
                url: '/aasmes/loadproductlist', headers:{'Content-Type':'application/json'},
                data: function(params){
                    var sparams =  {'q': params.term || '', 'page': params.page || 1};
                    var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
                    return JSON.stringify({ jsonrpc: "2.0", method: 'call', params: sparams, id: accessid});
                },
                processResults: function (data, params) {
                    params.page = params.page || 1;
                    var dresult = data.result;
                    return {
                        results: dresult.items,
                        pagination: {more: (params.page * 30) < dresult.total_count}
                    };
                }
            }
        });
        $('#materialcancel').click(function(){layer.close(layerindex);});
        $('#materialconfirm').click(function(){
            var productid = $('#mesmaterial').val();
            if(productid==null || productid==''){
                layer.msg('您还未设置原料，请先设置要消耗的原料！', {icon: 5});
                return ;
            }
            var consumeqty = $('#materialqty').val();
            if(!isAboveZeroFloat(consumeqty)){
                layer.msg('原料消耗数量必须是一个大于0的数！', {icon: 5});
                return ;
            }
            action_loading_consumeinformation(meslineid, parseInt(productid), parseFloat(consumeqty));
            layer.close(layerindex);
        });
    });

    function action_loading_consumeinformation(meslineid, productid, productqty){
        var temparams = {'meslineid': meslineid, 'materialid': productid, 'materialqty': productqty};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/repairing/finish/loadstock',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:30000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var temptr = $('<tr class="aas-material"></tr>').attr({
                    'meslineid': meslineid, 'materialid': productid,'materialqty': productqty
                }).appendTo($('#materiallist'));
                $('<td></td>').html(dresult.materialcode).appendTo(temptr);
                $('<td></td>').html(productqty).appendTo(temptr);
                $('<td></td>').html(dresult.stockqty).appendTo(temptr);
                var opttd = $('<td style="cursor: pointer;"></td>').appendTo(temptr);
                $('<span class="label label-danger pull-right">删除</span>').appendTo(opttd);
                opttd.click(function(){
                    $(this).parent().remove();
                });
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
            }
        });
    }

});