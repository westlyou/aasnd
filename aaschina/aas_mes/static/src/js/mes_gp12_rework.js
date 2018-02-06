/**
 * Created by luforn on 2017-11-16.
 */

$(function() {

    var scanable = true; //是否可以继续扫描
    new VScanner(function(barcode) {
        if (barcode == null || barcode == '') {
            scanable = true;
            layer.msg('扫描条码异常！', {icon: 5});
            return;
        }
        action_scan_serialnumber(barcode);
    });


    //扫描隔离板
    function action_scan_serialnumber(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var workstationid = $('#mes_workstation').attr('workstationid');
        if (workstationid==null || workstationid=='0' || workstationid==''){
            layer.msg('当前未绑定工位，请绑定工位再继续操作！', {icon: 5});
            scanable = true;
            return ;
        }
        var scannerid = $('#mes_employee').attr('employeeid');
        if (scannerid==null || scannerid=='0' || scannerid==''){
            layer.msg('当前工位没有扫描员在岗，请先让扫描员上岗再操作！', {icon: 5});
            scanable = true;
            return ;
        }
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/gp12/rework/scanserialnumber',
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
                if($('#serialnumber_'+dresult.serialnumber_id).length > 0){
                    layer.msg('已扫描，请不要重复操作！', {icon: 5});
                    return ;
                }
                $('#mes_serialnumber').html(barcode);
                $('#mes_productcode').html(dresult.product_code);
                if(dresult.message!=null && dresult.message!=''){
                    $('#checkwarning').html(dresult.message);
                }
                var serialnumberli = $('<li class="aas-serialnumber"></li>').prependTo($('#serialnumberlist'));
                serialnumberli.attr({
                    'serialnumberid': dresult.serialnumber_id, 'id': 'serialnumber_'+dresult.serialnumber_id
                }).html('<a href="javascript:void(0);">'+dresult.serialnumber_name+'</a>');
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    $('#mes_badmode').select2({
        placeholder: '不良模式..........',
        ajax:{
            type: 'post',
            timeout:10000,
            dataType: 'json',
            url: '/aasmes/badmodelist',
            headers:{'Content-Type':'application/json'},
            data: function(params){
                var sparams =  {
                    'q': params.term || '', 'page': params.page || 1
                };
                return JSON.stringify({ jsonrpc: "2.0", method: 'call', params: sparams, id: Math.floor(Math.random() * 1000 * 1000 * 1000) })
            },
            processResults: function (data, params) {
                params.page = params.page || 1;
                var dresult = data.result;
                return {
                    results: dresult.items,
                    pagination: {
                        more: (params.page * 30) < dresult.total_count
                    }
                };
            }
        }
    });

    $('#action_commit_badmode').click(function(){
        layer.confirm('您确认是上传不良？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            var serialnumberlist = $('li.aas-serialnumber');
            if(serialnumberlist==undefined || serialnumberlist==null || serialnumberlist.length<= 0){
                layer.msg('你还未扫描不良品！', {icon: 5});
                return ;
            }
            var serialnumberids = [];
            $.each(serialnumberlist, function(index, tserialnumber){
                serialnumberids.push(parseInt($(tserialnumber).attr('serialnumberid')));
            });
            var commitparams = {'serialnumberlist': serialnumberids};
            var workstationid = parseInt($('#mes_workstation').attr('workstationid'));
            if(workstationid==0){
                layer.msg('当前登录用户可能还未绑定GP12库位，请联系领班设置库位信息！', {icon: 5});
                return ;
            }
            var employeeid = parseInt($('#mes_employee').attr('employeeid'));
            if(employeeid==0){
                layer.msg('当前还未添加操作员工，请先扫描员工牌添加操作员！', {icon: 5});
                return ;
            }
            commitparams['employee_id'] = employeeid;
            var badmodeid = parseInt($('#mes_badmode').val());
            if(badmodeid==0){
                layer.msg('请先选择不良模式！', {icon: 5});
                return ;
            }
            commitparams['badmode_id'] = badmodeid;
            scanable = false;
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            $.ajax({
                url: '/aasmes/gp12/rework/actioncommit',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: commitparams, id: access_id}),
                success:function(data){
                    scanable = true;
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    window.location.reload(true);
                },
                error:function(xhr,type,errorThrown){
                    scanable = true;
                    console.log(type);
                }
            });
        },function(){});
    });

    $('#action_back_checking').click(function(){
        layer.confirm('您确认是返回检测操作？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            window.location.replace('/aasmes/gp12/checking');
        },function(){});
    });


});
