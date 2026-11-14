# Fusion Described Save v1.0.5
# Autodesk Fusion Python Add-In

import adsk.core
import adsk.fusion
import traceback

_app = None
_ui = None
_handlers = []
_custom_save_event = None
_custom_save_handler = None

ADDIN_NAME = 'FusionDescribedSave'
COMMAND_ID = 'FusionDescribedSaveCommandV10'
COMMAND_NAME = '説明付き保存'
COMMAND_DESCRIPTION = '説明を入力して、現在のデザインを説明付きで保存します。'
CUSTOM_EVENT_ID = 'FusionDescribedSaveDeferredEventV10'

def _show_message(message):
    try:
        if _ui:
            _ui.messageBox(message, ADDIN_NAME)
    except:
        pass

def refresh_ui():
    """UI（ファイルメニュー）の状態を監視し、ボタンが死んでいたら再構築する"""
    try:
        if not _ui: return
        qat = _ui.toolbars.itemById('QAT')
        if not qat: return
        
        file_menu = None
        for ctrl in qat.controls:
            if ctrl.objectType == adsk.core.DropDownControl.classType():
                if 'file' in ctrl.id.lower() or 'app' in ctrl.id.lower():
                    file_menu = ctrl
                    break

        cmd_def = _ui.commandDefinitions.itemById(COMMAND_ID)
        if not cmd_def: return

        if file_menu:
            # 既存のボタンがあれば一度削除してクリーンにする（ゾンビ化対策）
            existing_ctrl = file_menu.controls.itemById(COMMAND_ID)
            if existing_ctrl:
                existing_ctrl.deleteMe()
            
            # 新鮮なボタンを再配置
            try:
                new_ctrl = file_menu.controls.addCommand(cmd_def, 'ExportCommand')
            except:
                try:
                    new_ctrl = file_menu.controls.addCommand(cmd_def, 'SaveAsCommand')
                except:
                    new_ctrl = file_menu.controls.addCommand(cmd_def)
                    
            if new_ctrl:
                new_ctrl.isVisible = True
    except:
        pass


class SaveCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmd = args.command
            on_execute = SaveCommandExecuteHandler()
            cmd.execute.add(on_execute)
            _handlers.append(on_execute)
        except:
            _show_message('入力ポップアップの準備中にエラーが発生しました。\n\n' + traceback.format_exc())

class SaveCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            description, cancelled = _ui.inputBox('バージョンの説明を入力してください。', '説明付き保存', '')
            if cancelled: return
            description = (description or '').strip()
            if not description:
                _show_message('バージョンの説明が空欄のため、保存を中止しました。')
                return
            doc = _app.activeDocument
            if not doc:
                _show_message('保存するドキュメントが開かれていません。')
                return
            if not doc.isSaved:
                _show_message('このドキュメントはまだ一度も保存されていません。\n\n先にFusion標準の「名前を付けて保存」で保存先とファイル名を指定してください。')
                return
            _app.fireCustomEvent(CUSTOM_EVENT_ID, description)
        except:
            _show_message('保存要求の準備中にエラーが発生しました。\n\n' + traceback.format_exc())

class DeferredSaveEventHandler(adsk.core.CustomEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            description = (args.additionalInfo or '').strip()
            if not description: return
            doc = _app.activeDocument
            if not doc: return
            if not doc.isSaved: return
            result = doc.save(description)
            if result:
                _show_message('説明付きで保存しました。\n\nバージョンの説明：\n' + description)
            else:
                _show_message('Fusionが保存に失敗したと報告しました。ネットワーク接続やデータパネルを確認してください。')
        except:
            _show_message('説明付き保存中にエラーが発生しました。\n\n' + traceback.format_exc())


# ==========================================
# 環境（ワークスペース）切り替え検知用リスナー
# ==========================================
class WorkspaceActivatedHandler(adsk.core.WorkspaceEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        # 3D PCB等に切り替わった瞬間にボタンを再構築
        refresh_ui()

class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        # 別タブ等に切り替わった瞬間にボタンを再構築
        refresh_ui()


def run(context):
    global _app, _ui, _custom_save_event, _custom_save_handler
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        
        adsk.autoTerminate(False)

        _custom_save_event = _app.registerCustomEvent(CUSTOM_EVENT_ID)
        _custom_save_handler = DeferredSaveEventHandler()
        _custom_save_event.add(_custom_save_handler)
        _handlers.append(_custom_save_handler)

        cmd_def = _ui.commandDefinitions.itemById(COMMAND_ID)
        if not cmd_def:
            cmd_def = _ui.commandDefinitions.addButtonDefinition(
                COMMAND_ID, COMMAND_NAME, COMMAND_DESCRIPTION
            )

        on_created = SaveCommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        # ワークスペース/ドキュメント切り替え時にUIをリフレッシュするイベントを登録
        on_workspace_activated = WorkspaceActivatedHandler()
        _ui.workspaceActivated.add(on_workspace_activated)
        _handlers.append(on_workspace_activated)

        on_document_activated = DocumentActivatedHandler()
        _app.documentActivated.add(on_document_activated)
        _handlers.append(on_document_activated)

        # 初回起動時のUI構築
        refresh_ui()

    except:
        _show_message('起動中にエラーが発生しました。\n\n' + traceback.format_exc())


def stop(context):
    global _app, _ui, _custom_save_event, _custom_save_handler
    try:
        if _ui:
            qat = _ui.toolbars.itemById('QAT')
            if qat:
                for ctrl in qat.controls:
                    if ctrl.objectType == adsk.core.DropDownControl.classType() and ('file' in ctrl.id.lower() or 'app' in ctrl.id.lower()):
                        for c_id in (COMMAND_ID, 'FusionDescribedSaveCommandV9', 'FusionDescribedSaveCommandV10'):
                            control = ctrl.controls.itemById(c_id)
                            if control: control.deleteMe()
                            
                for c_id in (COMMAND_ID, 'FusionDescribedSaveCommandV9', 'FusionDescribedSaveCommandV10'):
                    control = qat.controls.itemById(c_id)
                    if control: control.deleteMe()

            for command_id in (COMMAND_ID, 'FusionDescribedSaveCommandV9', 'FusionDescribedSaveCommandV10'):
                cmd_def = _ui.commandDefinitions.itemById(command_id)
                if cmd_def: cmd_def.deleteMe()

        if _app:
            for event_id in (CUSTOM_EVENT_ID, 'FusionDescribedSaveDeferredEventV9', 'FusionDescribedSaveDeferredEventV10'):
                try:
                    _app.unregisterCustomEvent(event_id)
                except:
                    pass
    except:
        pass
    finally:
        _handlers.clear()
        _custom_save_event = None
        _custom_save_handler = None
        _app = None
        _ui = None