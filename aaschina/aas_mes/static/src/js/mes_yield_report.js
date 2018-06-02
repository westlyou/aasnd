/**
 * Created by luforn on 2018-6-1.
 */

$(function() {

    $("#checkall").click(function () {
        var clicked = $(this).data('clicked');
        if (clicked) {
            $(".mailbox-messages input[type='checkbox']").iCheck("uncheck");
            $(".fa", this).removeClass("fa-check-square-o").addClass('fa-square-o');
        } else {
            $(".mailbox-messages input[type='checkbox']").iCheck("check");
            $(".fa", this).removeClass("fa-square-o").addClass('fa-check-square-o');
        }
        $(this).data("clicked", !clicked);
    });

    function gettoday(){
        var tempdate = new Date();
        var tyear = tempdate.getFullYear();
        var tmonth = tempdate.getMonth() + 1;
        var tdate = tempdate.getDate();
        if(tmonth>=1 && tmonth<=9){
            tmonth = "0" + tmonth;
        }
        if(tdate>=1 && tdate<=9){
            tdate = "0"+tdate;
        }
        return tyear+'-'+tmonth+'-'+tdate;
    }

    $('#querydate').val(gettoday());

    $('#querydate').datepicker({clearBtn: true, autoclose: true, language: 'zh-CN', format: 'yyyy-mm-dd'});

    // 自动加载不良模式
    function action_loading_baodmodelist(){
        var badmodeheaders = $('.aas-badmode');
        if(badmodeheaders!=undefined && badmodeheaders!=null && badmodeheaders.length > 0){
            badmodeheaders.remove();
        }
        var workdate = $('#querydate').val();
        if(workdate==undefined || workdate==null || workdate==''){
            layer.msg('请先设置投产日期！', {icon: 5});
            return ;
        }
        var meslineid = parseInt($('#workorderlist').attr('meslineid'));
        var temparams = {'meslineid': meslineid, 'workdate': workdate};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/yieldreport/badmodelist',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 30000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var page = 1;
                var querydate = $('#querydate').val();
                var productcode = $('#queryproduct').val();
                var workorder = $('#queryworkorder').val();
                if(dresult.badmodelist.length<=0){
                    localStorage.setItem('mesline-badmode-'+meslineid, '');
                    action_loading_workorderlist(page, querydate, productcode, workorder);
                    return ;
                }
                var badmodeids = [];
                var tableheader = $('#yieldheaderline');
                $.each(dresult.badmodelist, function(index, badmode){
                    badmodeids.push(badmode.badmode_id);
                    $('<th class="aas-badmode"></th>').html(badmode.badmode_name).appendTo(tableheader);
                });
                localStorage.setItem('mesline-badmode-'+meslineid, badmodeids.join(','));
                action_loading_workorderlist(page, querydate, productcode, workorder);
            },
            error: function (xhr, type, errorThrown) {
                console.log(type);
            }
        });
    }

    function action_loading_workorderlist(page, workdate, productcode, workorder){
        var meslineid = parseInt($('#workorderlist').attr('meslineid'));
        var tparams = {'meslineid': meslineid};
        if(page > 0){
            tparams['page'] = page;
        }
        if(workdate==undefined || workdate==null || workdate==''){
            layer.msg('请先设置投产日期！', {icon: 5});
            return ;
        }
        tparams['workdate'] = workdate;
        if(productcode!=undefined && productcode!=null && productcode!=''){
            tparams['productcode'] = productcode;
        }
        if(workorder!=undefined && workorder!=null &&workorder!=''){
            tparams['workorder'] = workorder;
        }
        var tempid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/yieldreport/workorderlist',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 30000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tparams, id: tempid}),
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#workorderlist').html('');
                $('#recordcountcontent').html(dresult.countcontent);
                $('#recordcountcontent').attr('total', dresult.total);
                var badmodeidstr = localStorage.getItem('mesline-badmode-'+meslineid);
                var badmodeids = [];
                if(badmodeidstr!=null && badmodeidstr!=''){
                    badmodeids = badmodeidstr.split(',');
                }
                if(dresult.workorderlist==null || dresult.workorderlist.length==0){
                    return ;
                }
                var linetype = dresult.linetype;
                $.each(dresult.workorderlist, function(index, workorder){
                    var wkline = $('<tr></tr>').appendTo($('#workorderlist'));
                    $('<td></td>').html('<input type="checkbox" orderid="'+workorder.workorder_id+'"/>').appendTo(wkline);
                    $('<td></td>').html(workorder.plan_date).appendTo(wkline);
                    $('<td></td>').html(workorder.plan_schedule).appendTo(wkline);
                    $('<td></td>').html(workorder.mainorder_name).appendTo(wkline);
                    $('<td></td>').html(workorder.workorder_name).appendTo(wkline);
                    $('<td></td>').html(workorder.product_code).appendTo(wkline);
                    $('<td></td>').html(workorder.produce_start).appendTo(wkline);
                    $('<td></td>').html(workorder.produce_finish).appendTo(wkline);
                    $('<td></td>').html(workorder.input_qty).appendTo(wkline);
                    $('<td></td>').html(workorder.output_qty).appendTo(wkline);
                    $('<td></td>').html(workorder.reach_rate.toFixed(2)).appendTo(wkline);
                    $('<td></td>').html(workorder.badmode_qty).appendTo(wkline);
                    $('<td></td>').html(workorder.yield_actual.toFixed(2)).appendTo(wkline);
                    if(linetype=='flowing'){
                        $('<td></td>').html(workorder.once_qty).appendTo(wkline);
                        $('<td></td>').html(workorder.twice_qty).appendTo(wkline);
                        $('<td></td>').html(workorder.more_qty).appendTo(wkline);
                    }
                    var badmodes = workorder.badmodes;
                    if(badmodeids.length==0){
                        return ;
                    }
                    $.each(badmodeids, function(index, bmid){
                        var tempqty = 0.0;
                        var tempid = parseInt(bmid);
                        if(badmodes.hasOwnProperty(tempid)){
                            tempqty = badmodes[tempid];
                        }
                        $('<td></td>').html(tempqty).appendTo(wkline);
                    });
                });
                $('.mailbox-messages input[type="checkbox"]').iCheck({checkboxClass: 'icheckbox_flat-blue'});
                $(".mailbox-messages input[type='checkbox']").on('ifChecked', function(event){
                    $(this).addClass('aas-active');
                });
                $(".mailbox-messages input[type='checkbox']").on('ifUnchecked', function(event){
                    $(this).removeClass('aas-active');
                    if($('.fa', '#checkall').hasClass('fa-check-square-o')){
                        $('.fa', '#checkall').removeClass("fa-check-square-o").addClass('fa-square-o');
                    }
                });
            },
            error: function (xhr, type, errorThrown) {
                console.log(type);
            }
        });
    }

    //加载不良模式
    action_loading_baodmodelist();


    $('#action_prepage').click(function(){
        var page = parseInt($('#recordcountcontent').attr('page'));
        if(page <= 1){
            layer.msg('当前已经是第一页了！', {icon: 5});
            return ;
        }
        page -= 1;
        $('#recordcountcontent').attr('page', page);
        var workdate = $('#querydate').val();
        var productcode = $('#queryproduct').val();
        var workorder = $('#queryworkorder').val();
        if(productcode!=null && productcode!=''){
            productcode = productcode.trim();
        }
        if(workorder!=null && workorder!=''){
            workorder = workorder.trim();
        }
        action_loading_workorderlist(page, workdate, productcode, workorder);
    });

    $('#action_nxtpage').click(function(){
        var page = parseInt($('#recordcountcontent').attr('page'));
        var total = parseInt($('#recordcountcontent').attr('total'));
        if(page*100 >= total){
            layer.msg('当前已经是第后一页了！', {icon: 5});
            return ;
        }
        page += 1;
        $('#recordcountcontent').attr('page', page);
        var workdate = $('#querydate').val();
        var productcode = $('#queryproduct').val();
        var workorder = $('#queryworkorder').val();
        if(productcode!=null && productcode!=''){
            productcode = productcode.trim();
        }
        if(workorder!=null && workorder!=''){
            workorder = workorder.trim();
        }
        action_loading_workorderlist(page, workdate, productcode, workorder);
    });


    //查询
    $('#querybtn').click(function(){
        $('#recordcountcontent').attr('page', 1);
        action_loading_baodmodelist();
    });

    //导出
    $('#exportbtn').click(function(){
        action_export_datas()
    });


    function action_export_datas(){
        var meslineid = parseInt($('#workorderlist').attr('meslineid'));
        var searchkey = '?meslineid='+meslineid;
        var workorderlist = $('input.aas-active');
        if(workorderlist!=undefined && workorderlist!=null && workorderlist.length > 0){
            workorderids = [];
            $.each(workorderlist, function(index, ordeript){
                workorderids.push($(ordeript).attr('orderid'));
            });
            searchkey += '&workorderidstr='+workorderids.join('-');
            window.open('/aasmes/yieldreport/export'+searchkey);
        }else{
            var tempparams = {'meslineid': meslineid};
            var workdate = $('#querydate').val();
            if(workdate==null || workdate==''){
                layer.msg('请先设置投产日期！', {icon: 5});
                return ;
            }
            searchkey += '&workdate='+workdate;
            tempparams['workdate'] = workdate;
            var productcode = $('#queryproduct').val();
            if(productcode!=null && productcode!=''){
                searchkey += '&productcode='+productcode;
                tempparams['productcode'] = productcode;
            }
            var workorder = $('#queryworkorder').val();
            if(workorder!=null && workorder!=''){
                searchkey += '&workorder='+workorder;
                tempparams['workorder'] = workorder;
            }
            var tempid = Math.floor(Math.random() * 1000 * 1000 * 1000);
            $.ajax({
                url: '/aasmes/yieldreport/exportchecking',
                headers: {'Content-Type': 'application/json'},
                type: 'post', timeout: 30000, dataType: 'json',
                data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tempparams, id: tempid}),
                success: function (data) {
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    window.open('/aasmes/yieldreport/export'+searchkey);
                },
                error: function (xhr, type, errorThrown) {
                    console.log(type);
                }
            });
        }
    }

});