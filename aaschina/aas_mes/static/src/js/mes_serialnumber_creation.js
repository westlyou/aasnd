/**
 * Created by luforn on 2017-10-12.
 */

$(function() {

    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    $('#action_addserial').click(function(){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/serialnumber/checkingmesline',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {}, id: access_id}),
            success:function(data){
                var dresult = data.result;
                $('#serial_supplier').innerHTML = dresult.serial_supplier;
                $('#serial_mesline').innerHTML = dresult.mesline_name;
                $('#serial_year').innerHTML = dresult.serial_year;
                $('#serial_week').innerHTML = dresult.serial_week;
                $('#serial_weekday').innerHTML = dresult.serial_weekday;
                $('#serial_type').innerHTML = dresult.serial_type;
                $('#serial_extend').innerHTML = dresult.serial_extend;
                $('#customer_code').innerHTML = dresult.customer_code;
                $('#product_code').innerHTML = dresult.product_code;
                $('#serial_message').innerHTML = dresult.message;
                $('#serial_count').html(dresult.serial_count);
                $('#lastserialnumber').html(dresult.lastserialnumber);
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                layer.prompt({title: '输入序列号数量，并确认', formType: 3}, function(text, index){
                    if(!isAboveZeroFloat(text)){
                        layer.msg('序列号的数量必须是一个大于零的整数！', {icon: 5});
                        return ;
                    }
                    layer.close(index);
                    var serialcount = parseInt(text);
                    var tempid = Math.floor(Math.random() * 1000 * 1000 * 1000);
                    $.ajax({
                        url: '/aasmes/serialnumber/adddone',
                        headers: {'Content-Type': 'application/json'},
                        type: 'post', timeout: 10000, dataType: 'json',
                        data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'serialcount': serialcount}, id: tempid}),
                        success: function (data) {
                            $('#serialnumberlist').html('');
                            var dresult = data.result;
                            if(!dresult.success){
                                layer.msg(dresult.message, {icon: 5});
                                return ;
                            }
                            _.each(dresult.serialnumbers, function(serialnumber){
                                var serialitem = $("<tr class='aas-serialnumber'></tr>");
                                serialitem.attr({'serialid': serialnumber.serialid});
                                var serialcontent = "<td>"+serialnumber.serialname+"</td>";
                                serialcontent += "<td>"+serialnumber.sequencecode+"</td>";
                                serialcontent += "<td>"+serialnumber.product_code+"</td>";
                                serialcontent += "<td>"+serialnumber.customer_code+"</td>";
                                serialitem.html(serialcontent);
                                $('#serialnumberlist').append(serialitem);
                            });
                            $('#serial_count').html(dresult.serial_count);
                            $('#lastserialnumber').html(dresult.lastserialnumber);
                        },
                        error: function (xhr, type, errorThrown) {
                            console.log(type);
                        }
                    });
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

    $('#printerlist').select2({
        placeholder: '选择标签打印机',
        ajax:{
            type: 'post',
            timeout:10000,
            dataType: 'json',
            url: '/aasmes/printerlist',
            headers:{'Content-Type':'application/json'},
            data: function(params){
                var sparams =  {'q': params.term || '', 'page': params.page || 1};
                var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
                return JSON.stringify({ jsonrpc: "2.0", method: 'call', params: sparams, id: accessid})
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

    //打印标签
    $('#action_printing').click(function(){
        var printerid = $('#printerlist').val();
        if(printerid==null || printerid=='0'){
            layer.msg('请先设置好标签打印机！', {icon: 5});
            return ;
        }
        var serialnumbertrs = $('tr.aas-serialnumber');
        if(serialnumbertrs==undefined || serialnumbertrs==null || serialnumbertrs.length <= 0){
            layer.msg('请确认，您还没有生成需要打印的标签！', {icon: 5});
            return ;
        }
        var printerid = parseInt(printerid);
        var serialids = [];
        $.each(serialnumbertrs, function(index, serialnumber){
            var serialid = parseInt($(serialnumber).attr('serialid'));
            serialids.push(serialid);
        });
        var params = {'printerid': printerid, 'serialids': serialids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/serialnumber/loadingserialnumbers',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 10000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: params, id: access_id}),
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var printername = dresult.printer;
                var printcount = 1 ;
                var printerurl = dresult.serverurl;
                _(dresult.records).each(function(record){
                    var params = {'label_name': printername, 'label_count': printcount, 'label_content':record};
                    $.ajax({type:'post', dataType:'script', url:'http://'+printerurl, data: params,
                        success: function (result) { },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                });

            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

});