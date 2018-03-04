/**
 * Created by luforn on 2018-3-3.
 */

$(function(){


    function isAASFloat(val){
        var reg = /^(-?\d+)(\.\d+)?$/;
        if(reg.test(val)){
            return true;
        }
        return false;
    }

    //提交检测值
    $('#action_commit').click(function(){
        var equipmentid = $('#mes_equipment').attr('equipmentid');
        if(equipmentid==undefined || equipmentid==null || equipmentid=='0'){
            layer.msg('设备异常，您是否经过有效途径打开当前页面！', {icon: 5});
            return ;
        }
        var employeeid = $('#mes_employee').attr('employeeid');
        if(employeeid==undefined || employeeid==null || employeeid=='0'){
            layer.msg('员工异常，您是否经过有效途径打开当前页面！', {icon: 5});
            return ;
        }
        var workorderid = $('#mes_wireorder').attr('workorderid');
        if(workorderid==undefined || workorderid==null || workorderid=='0'){
            layer.msg('工单异常，您是否经过有效途径打开当前页面！', {icon: 5});
            return ;
        }
        var parameterlist = $('input.aas-parameter');
        if(parameterlist==undefined || parameterlist.length<=0){
            layer.msg('检测参数异常，请先检查是否设置了检测参数！', {icon: 5});
            return ;
        }
        var paramlist = [];
        var messagelist = [];
        $.each(parameterlist, function(index, tempipt){
            var pflag = true;
            var tempval = $(tempipt).val();
            var parentdiv = $(tempipt).parent();
            var pid = parseInt(parentdiv.attr('pid'));
            var pname = parentdiv.attr('pname');
            var ptype = parentdiv.attr('ptype');
            if(tempval==null || tempval==''){
                pflag = false;
                messagelist.push('参数：'+pname+'还未设置检测值');
            }
            if(ptype=='number' && !isAASFloat(tempval)){
                pflag = false;
                messagelist.push('参数：'+pname+'检测值不是一个有效数值');
            }
            var superdiv = parentdiv.parent();
            if(pflag){
                if(superdiv.hasClass('has-error')){
                    superdiv.removeClass('has-error');
                }
                paramlist.push({'parameter_id': pid, 'parameter_value': tempval});
            }else if(!superdiv.hasClass('has-error')){
                superdiv.addClass('has-error');
            }
        });
        if(messagelist.length > 0){
            layer.msg(messagelist.join(';'), {icon: 5});
            return ;
        }
        if(paramlist.length <= 0){
            layer.msg('检测参数异常，当前未获取到有效的检测参数信息！', {icon: 5});
            return ;
        }
        var testtype = $('#action_commit').attr('testtype');
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var producttestid = parseInt($('#mes_producttest').attr('producttestid'));
        var testparams = {
            'testtype': testtype,
            'workorderid': parseInt(workorderid), 'producttestid': producttestid,
            'equipmentid': parseInt(equipmentid), 'employeeid': parseInt(employeeid), 'parameters': paramlist
        };
        $.ajax({
            url: '/aasmes/wirecutting/producttest/docommit',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: testparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                window.location.replace('/aasmes/wirecutting/producttest/orderdetail/'+dresult.orderid);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });

    });


});
