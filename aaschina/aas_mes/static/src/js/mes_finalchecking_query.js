/**
 * Created by luforn on 2018-1-16.
 */

$(function(){

    $('#querydatetime').daterangepicker({
        timePicker : true,
        timePicker24Hour: true,
        timePickerSeconds: true,
        locale: {
            separator: '~',
            applyLabel: '确定',
            cancelLabel: '取消',
            fromLabel: '起始时间',
            toLabel: '结束时间',
            customRangeLabel: '自定义',
            format: 'YYYY-MM-DD HH:mm:ss',
            daysOfWeek: ['日', '一', '二', '三', '四', '五', '六'],
            monthNames: ['一月', '二月', '三月', '四月', '五月', '六月',
               '七月', '八月', '九月', '十月', '十一月', '十二月'],
            firstDay: 1
        }
    });

    $('#mesproduct').select2({
        placeholder: '选择产品',
        ajax:{
            type: 'post',
            timeout:10000,
            dataType: 'json',
            url: '/aasmes/loadproductlist',
            headers:{'Content-Type':'application/json'},
            data: function(params){
                var sparams =  {'q': params.term || '', 'page': params.page || 1};
                return JSON.stringify({
                    jsonrpc: "2.0", method: 'call', params: sparams, id: Math.floor(Math.random() * 1000 * 1000 * 1000)
                });
            },
            processResults: function (data, params) {
                params.page = params.page || 1;
                var dresult = data.result;
                return {results: dresult.items, pagination: {more: (params.page * 20) < dresult.total_count}};
            }
        }
    });

    //产出查询
    $('#querybtn').click(function(){
        var warnmessage = $('#finalchecking').attr('message');
        if (warnmessage!=null && warnmessage!=''){
            layer.msg(warnmessage, {icon: 5});
            return ;
        }
        var meslineid = parseInt($('#finalchecking').attr('meslineid'));
        if(meslineid==0 || meslineid==null){
            layer.msg('当前登录用户可能未绑定产线工位，暂不可以查询产出记录！', {icon: 5});
            return ;
        }
        var querytime = $('#querydatetime').val();
        if(querytime==null || querytime==''){
            layer.msg('请设置查询的开始和结束时间', {icon: 5});
            return ;
        }
        var temptimes = querytime.split('~');
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var tempparams = {'meslineid': meslineid, 'starttime': temptimes[0], 'finishtime': temptimes[1]};
        $.ajax({
            url: '/aasmes/finalchecking/query/loadrecords',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: tempparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.records.length <= 0){
                    return ;
                }
                $.each(dresult.records, function(index, record){
                    var temptr = $('<tr></tr>').appendTo($('#outputlist'));
                    var tempcontent = "<td>"+record.product_code+"</td>";
                    tempcontent += "<td>"+record.mesline_name+"</td>";
                    tempcontent += "<td>"+record.workstation_name+"</td>";
                    tempcontent += "<td>"+record.output_date+"</td>";
                    tempcontent += "<td>"+record.product_qty+"</td>";
                    tempcontent += "<td>"+record.once_qty+"</td>";
                    tempcontent += "<td>"+record.twice_total_qty+"</td>";
                    tempcontent += "<td>"+record.once_rate+"%</td>";
                    tempcontent += "<td>"+record.twice_rate+"%</td>";
                    temptr.html(tempcontent);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });


    });


});
