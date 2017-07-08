/**
 * Created by Luforn on 2017-6-19.
 */

odoo.define('aas.base', function (require) {
    "use strict";

    var core = require('web.core');
    var data = require('web.data');
    var pyeval = require('web.pyeval');
    var Sidebar = require('web.Sidebar');
    var framework = require('web.framework');
    var WebClient = require('web.WebClient');
    var ListView = require('web.ListView');
    var FormView = require('web.FormView');
    var Model = require('web.DataModel');
    var session = require('web.session');
    var Dialog = require('web.Dialog');
    var crash_manager = require('web.crash_manager');

    var QWeb = core.qweb;
    var _t = core._t;


    WebClient.include({
        init: function() {
            this._super.apply(this, arguments);
            this.set('title_part', {"zopenerp": document.title});
        }
    });


    Sidebar.include({
        add_items: function(section_code, items) {
            //清理系统自带导出
            var export_label = _t("Export");
            var tempsuper = _.bind(this._super, this);
            if (section_code == 'other') {
                for (var i = 0; i < items.length; i++) {
                    if (items[i]['label'] == export_label) {
                        items.splice(i, 1)
                    }
                }
            }
            tempsuper.call(self, section_code, items);
        }
    });

    FormView.include({
        is_action_enabled: function(action) {
            var attrs = this.fields_view.arch.attrs;
            if(action=='labelprint'){
                return (action in attrs) ? JSON.parse(attrs[action]) : false;
            }
            return (action in attrs) ? JSON.parse(attrs[action]) : true;
        },
        render_sidebar: function($node) {
            var tempsuper = _.bind(this._super, this);
            tempsuper.call(self, $node);
            var self = this;
            if (!self.sidebar) {
                self.sidebar = new Sidebar(self, {editable: self.is_action_enabled('edit')});
                $node = $node || self.$('.oe_form_sidebar');
                self.sidebar.appendTo($node);
                self.toggle_sidebar();
            }
            if(self.is_action_enabled('labelprint')){
                self.sidebar.add_items('print', _.compact([
                    { label: '标签打印', callback: self.on_sidebar_printlabel }
                ]));
            }
        },
        on_sidebar_printlabel: function(){
            new AASLabelPrint(this, this.dataset).open();
        }
    });


    ListView.include({
        init: function (parent, dataset, view_id, options) {
            this._super.apply(this, arguments);
        },
        is_action_enabled: function(action) {
            var attrs = this.fields_view.arch.attrs;
            if(action=='orderimport' || action=='import' || action=='labelprint'){
                return (action in attrs) ? JSON.parse(attrs[action]) : false;
            }
            return (action in attrs) ? JSON.parse(attrs[action]) : true;
        },
        render_buttons: function() {
            var self = this;
            var add_button = false;
            if (!this.$buttons) { // Ensures that this is only done once
                add_button = true;
            }
            this._super.apply(this, arguments); // Sets this.$buttons
            if(add_button && this.$buttons) {
                this.$buttons.on('click', '.o_list_button_orderimport', this.do_aas_order_import);
            }
        },
        render_sidebar: function($node) {
            var tempsuper = _.bind(this._super, this);
            tempsuper.call(self, $node);
            var self = this;
            if (!self.sidebar) {
                self.sidebar = new Sidebar(self, {editable: self.is_action_enabled('edit')});
                $node = $node || self.options.$sidebar;
                self.sidebar.appendTo($node);
                self.sidebar.do_hide();
            }
            this.sidebar.add_items('other', _.compact([
                { label: '数据导出', callback: this.do_aas_web_export}
            ]));
            if (self.is_action_enabled('labelprint')){
               self.sidebar.add_items('print', _.compact([
                   { label: '标签打印', callback: this.do_aas_label_print}
               ]));
            }
        },
        do_aas_web_export: function(){
            new AASWebExporter(this, this.dataset).open();
        },
        do_aas_order_import: function(){
            new AASOrderImport(this, this.dataset).open();
        },
        do_aas_label_print: function(){
            new AASLabelPrint(this, this.dataset).open();
        }
    });

    var AASWebExporter = Dialog.extend({
        template: 'AASExportDialog',
        events: {
            'click .o_export_tree_item': function(e) {
                e.stopPropagation();
                var $elem = $(e.currentTarget);

                this.row_index = $elem.prevAll('.o_export_tree_item').length;
                this.row_index_level = $elem.parents('.o_export_tree_item').length;

                if(e.ctrlKey) {
                    $elem.toggleClass('o_selected').focus();
                } else if(e.shiftKey) {
                    $elem.addClass('o_selected').focus();
                } else {
                    this.$(".o_selected").removeClass("o_selected")
                    $elem.addClass("o_selected").focus();
                }
            },
            'dblclick .o_export_tree_item': function(e) {
                var $elem = $(e.currentTarget);
                $elem.removeClass('o_selected');
                this.add_field($elem.data('id'), $elem.find('.o_tree_column').first().text());
            },
            'keydown .o_export_tree_item': function(e) {
                e.stopPropagation();
                var $elem = $(e.currentTarget);
                var record = this.records[$elem.data('id')];

                switch(e.keyCode || e.which) {
                    case $.ui.keyCode.UP:
                        var $prev = $elem.prev('.o_export_tree_item');
                        $elem.removeClass("o_selected").blur();
                        $prev.addClass("o_selected").focus();
                        break;
                    case $.ui.keyCode.DOWN:
                        var $next = $elem.next('.o_export_tree_item');
                        if($next.length === 0) {
                            $next = $elem.parent('.o_export_tree_item').next('.o_export_tree_item');
                            if($next.length === 0) {
                                break;
                            }
                        }
                        $elem.removeClass("o_selected").blur();
                        $next.addClass("o_selected").focus();
                        break;
                }
            },

            'click .o_add_field': function() {
                var self = this;
                this.$('.o_field_tree_structure .o_selected')
                    .removeClass('o_selected')
                    .each(function() {
                        var $this = $(this);
                        self.add_field($this.data('id'), $this.children('.o_tree_column').text());
                    });
            },
            'click .o_remove_field': function() {
                this.$fields_list.find('option:selected').remove();
            },
            'click .o_remove_all_field': function() {
                this.$fields_list.empty();
            },
            'click .o_move_up': function() {
                var $selected_rows = this.$fields_list.find('option:selected');
                var $prev_row = $selected_rows.first().prev();
                if($prev_row.length){
                    $prev_row.before($selected_rows.detach());
                }
            },
            'click .o_move_down': function () {
                var $selected_rows = this.$fields_list.find('option:selected');
                var $next_row = $selected_rows.last().next();
                if($next_row.length){
                    $next_row.after($selected_rows.detach());
                }
            },

            'click .o_toggle_save_list': function(e) {
                e.preventDefault();

                var $saveList = this.$(".o_save_list");
                if($saveList.is(':empty')) {
                    $saveList.append(QWeb.render('Export.SaveList'));
                } else {
                    if($saveList.is(':hidden')) {
                        $saveList.show();
                        $saveList.find(".o_export_list_input").val("");
                    } else {
                        $saveList.hide();
                    }
                }
            },
            'click .o_save_list > button': function(e) {
                var $saveList = this.$(".o_save_list");
                var value = $saveList.find("input").val();
                if(!value) {
                    Dialog.alert(this, _t("Please enter save field list name"));
                    return;
                }
                var fields = this.get_fields();
                if (fields.length === 0) {
                    return;
                }
                $saveList.hide();
                var self = this;
                this.exports.create({
                    name: value,
                    resource: this.dataset.model,
                    export_fields: _.map(fields, function (field) {
                        return [0, 0, {name: field}];
                    })
                }).then(function(export_list_id) {
                    if(!export_list_id) {
                        return;
                    }
                    var $select = self.$(".o_exported_lists_select");
                    if($select.length === 0 || $select.is(":hidden")) {
                        self.show_exports_list();
                    }
                    $select.append(new Option(value, export_list_id));
                });
            },
        },
        init: function(parent, dataset) {
            var options = {
                title: '数据导出',
                buttons: [
                    {text: '导出', click: this.export_data, classes: "btn-primary"},
                    {text: '关闭', close: true},
                ],
            };
            this._super(parent, options);
            this.records = {};
            this.dataset = dataset;
            this.exports = new data.DataSetSearch(this, 'ir.exports', this.dataset.get_context());

            this.row_index = 0;
            this.row_index_level = 0;

            // The default for the ".modal_content" element is "max-height: 100%;"
            // but we want it to always expand to "height: 100%;" for this modal.
            // This can be achieved thanks to LESS modification without touching
            // the ".modal-content" rules... but not with Internet explorer (11).
            this.$modal.find(".modal-content").css("height", "100%");
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.$el.find('#fields_list').empty();
            self.$el.find('#field-tree-structure').remove();
            self.$fields_list = this.$('.o_fields_list');
            var got_fields = self.rpc("/web/export/get_fields", {
                model: self.dataset.model,
                import_compat: false,
            }).done(function (records) {
                self.on_show_data(records);
            });
            var waitFor = [got_fields];
            waitFor.push(this.getParent().get_active_domain().then(function (domain) {
                if (domain === undefined) {
                    self.ids_to_export = self.getParent().get_selected_ids();
                    self.domain = self.dataset.domain;
                } else {
                    self.ids_to_export = false;
                    self.domain = domain;
                }
                self.on_show_domain();
            }));
            waitFor.push(this.show_exports_list());
            return $.when.apply($, waitFor);
        },
        show_exports_list: function() {
            if (this.$('.o_exported_lists_select').is(':hidden')) {
                this.$('.o_exported_lists').show();
                return $.when();
            }

            var self = this;
            return this.exports.read_slice(['name'], {
                domain: [['resource', '=', this.dataset.model]]
            }).then(function (export_list) {
                if (!export_list.length) {
                    return;
                }
                self.$('.o_exported_lists').append(QWeb.render('Export.SavedList', {'existing_exports': export_list}));
                self.$('.o_exported_lists_select').on('change', function() {
                    self.$fields_list.empty();
                    var export_id = self.$('.o_exported_lists_select option:selected').val();
                    if(export_id) {
                        self.rpc('/web/export/namelist', {
                            model: self.dataset.model,
                            export_id: parseInt(export_id, 10),
                        }).then(do_load_export_field);
                    }
                });
                self.$('.o_delete_exported_list').click(function() {
                    var select_exp = self.$('.o_exported_lists_select option:selected');
                    if(select_exp.val()) {
                        self.exports.unlink([parseInt(select_exp.val(), 10)]);
                        select_exp.remove();
                        self.$fields_list.empty();
                        if (self.$('.o_exported_lists_select option').length <= 1) {
                            self.$('.o_exported_lists').hide();
                        }
                    }
                });
            });

            function do_load_export_field(field_list) {
                _.each(field_list, function (field) {
                    self.$fields_list.append(new Option(field.label, field.name));
                });
            }
        },
        on_show_domain: function() {
            this.$('p').first().after(QWeb.render('AASExport.DomainMessage', {record: this}));
        },
        on_show_data: function(records) {
            var self = this;
            var trecords = self.do_filter_fields(records);
            this.$('.o_left_field_panel').empty().append($("<div/>").addClass('o_field_tree_structure').append(QWeb.render('AASExport.TreeItems', {'fields': trecords})));
            _.extend(self.records, _.object(_.pluck(trecords, 'id'), trecords));
            this.$records = this.$(".o_export_tree_item");
            this.$records.each(function(i, el) {
                var $elem = $(el);
                $elem.find('.o_tree_column').first().toggleClass('o_required', !!self.records[$elem.data('id')].required);
            });
        },
        do_filter_fields: function(fields){
            var records = [];
            _.each(fields, function(record) {
                if(record.field_type=='one2many'){
                    return ;
                }else if(record.field_type=='binary'){
                    return ;
                }else if(record.id=='create_uid'){
                    return ;
                }else if(record.id=='create_date'){
                    return ;
                }else if(record.id=='.id'){
                    return ;
                }else if(record.id=='__last_update'){
                    return ;
                }else if(record.id=='write_uid'){
                    return ;
                }else if(record.id=='write_date'){
                    return ;
                }else if(record.id=='parent_left'){
                    return ;
                }else if(record.id=='parent_right'){
                    return ;
                }else if(record.value.indexOf('/id')>=0){
                    record.value = record.id;
                }
                records.push(record);
            });
            return records;
        },
        add_field: function(field_id, string) {
            var $field_list = this.$('.o_fields_list');
            field_id = this.records[field_id].value || field_id;
            if($field_list.find("option[value='" + field_id + "']").length === 0) {
                $field_list.append(new Option(string, field_id));
            }
        },
        get_fields: function() {
            var $export_fields = this.$(".o_fields_list option").map(function() {
                return $(this).val();
            }).get();
            if($export_fields.length === 0) {
                Dialog.alert(this, _t("Please select fields to save export list..."));
            }
            return $export_fields;
        },
        export_data: function() {
            var self = this;
            var exported_fields = this.$('.o_fields_list option').map(function () {
                return {
                    name: (self.records[this.value] || this).value,
                    label: this.textContent || this.innerText // DOM property is textContent, but IE8 only knows innerText
                };
            }).get();
            if (_.isEmpty(exported_fields)) {
                Dialog.alert(this, _t("Please select fields to export..."));
                return;
            }
            framework.blockUI();
            this.session.get_file({
                url: '/web/export/xls',
                data: {data: JSON.stringify({
                    model: this.dataset.model,
                    fields: exported_fields,
                    ids: this.ids_to_export,
                    domain: this.domain,
                    context: pyeval.eval('contexts', [this.dataset._model.context()]),
                    import_compat: false
                })},
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(crash_manager)
            });
        }
    });


    var AASOrderImport = Dialog.extend({
        template: 'AASOrderImportDialog',
        init: function(parent, dataset) {
            var options = {
                title: '订单导入',
                buttons: [
                    {text: '导入', click: this.import_order, classes: "btn-primary"},
                    {text: '关闭', close: true},
                ],
            };
            this._super(parent, options);
            this.dataset = dataset;
            this.res_model = dataset.model;

            // The default for the ".modal_content" element is "max-height: 100%;"
            // but we want it to always expand to "height: 100%;" for this modal.
            // This can be achieved thanks to LESS modification without touching
            // the ".modal-content" rules... but not with Internet explorer (11).
            this.$modal.find(".modal-content").css("height", "200");
        },
        start: function() {
            this._super.apply(this, arguments);
        },
        import_order: function() {
            var self = this;
            var ordernumber = this.$('#order_number').val();
            if (ordernumber==null || ordernumber==''){
                Dialog.alert(this, "请先填入订单号..............");
                return;
            }
            var OrderModel = new Model(self.res_model);
            OrderModel.call('action_import_order',[ordernumber]).then(function(data){
                if(data.success==undefined || data.success){
                    self.close();
                }else{
                    self.do_warn('警告', data.message, false);
                }
            }, function(error,event) {
                if (event) {
                    event.preventDefault();
                }
                self.do_warn(error.message, error.data.message, false);
            });
        }
    });

    var AASLabelPrint = Dialog.extend({
        template: 'AASLabelPrintDialog',
        init: function(parent, dataset) {
            var options = {
                title: '标签打印',
                buttons: [
                    {text: '打印', click: this.print_label, classes: "btn-primary"},
                    {text: '关闭', close: true},
                ],
            };
            this._super(parent, options);
            this.dataset = dataset;
            this.res_model = dataset.model;

            // The default for the ".modal_content" element is "max-height: 100%;"
            // but we want it to always expand to "height: 100%;" for this modal.
            // This can be achieved thanks to LESS modification without touching
            // the ".modal-content" rules... but not with Internet explorer (11).
            this.$modal.find(".modal-content").css("height", "200");
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.$el.find('#label_printer').empty();
            var load_printers = self.rpc("/aas/base/labelprinters", {
                model: self.dataset.model
            }).done(function (records) {
                if (records.length<=0){
                    return ;
                }
                var printer_list = self.$el.find('#label_printer');
                _.each(records, function(record){
                    printer_list.append(new Option(record.pname, record.pid));
                });
            });
            var waitFor = [load_printers];
            var view_type = self.getParent().ViewManager.active_view.type;
            if (view_type=='list'){
                waitFor.push(self.getParent().get_active_domain().then(function (domain) {
                    if (domain === undefined) {
                        self.ids = self.getParent().get_selected_ids();
                        self.domain = self.dataset.domain;
                    } else {
                        self.ids = [];
                        self.domain = domain;
                    }
                }));
            }else if (view_type=='form'){
                self.ids = [self.getParent().datarecord.id];
                self.domain = [];
            }
            return $.when.apply($, waitFor);
        },
        print_label: function() {
            var self = this;
            var labelprinter = this.$('#label_printer').val();
            var labelcount = this.$('#label_count').val();
            if (labelprinter==null || labelprinter==''){
                Dialog.alert(this, "请先选择标签打印机..............");
                return;
            }
            var numberreg = /^[1-9]\d*$/;
            if(!numberreg.test(labelcount)){
                Dialog.alert(this, "标签份数必须是一个大于等于1的整数！");
                return;
            }
            var LabelModel = new Model(self.res_model);
            LabelModel.call('action_print_label',[parseInt(labelprinter), self.ids, self.domain]).then(function(data){
                if(data.success==undefined || data.success){
                    self.close();
                    var params = {'label_name': data.printer, 'label_count': parseInt(labelcount), 'label_content':data.records};
                    $.ajax({type:'post', dataType:'script', url:'http://'+data.serverurl, data: params,
                        success: function (result) { },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                }else{
                    self.do_warn('警告', data.message, false);
                }
            }, function(error,event) {
                if (event) {
                    event.preventDefault();
                }
                self.do_warn(error.message, error.data.message, false);
            });
        }
    });

    return {
        'AASWebExporter': AASWebExporter,
        'AASOrderImport': AASOrderImport,
        'AASLabelPrint': AASLabelPrint
    };

});
