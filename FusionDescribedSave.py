# Fusion Described Save v1.0.3
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
COMMAND_ID = 'FusionDescribedSaveCommandV8'
COMMAND_NAME = '説明付き保存'
COMMAND_DESCRIPTION = '説明を入力して、現在のデザインを説明付きで保存します。'
CUSTOM_EVENT_ID = 'FusionDescribedSaveDeferredEventV8'

def _show_message(message):
    try:
        if _ui:
            _ui.messageBox(message, ADDIN_NAME)
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
            description, cancelled = _ui.inputBox(
                'バージョンの説明を入力してください。',
                '説明付き保存',
                ''
            )
            if cancelled:
                return
            description = (description or '').strip()
            if not description:
                _show_message('バージョンの説明が空欄のため、保存を中止しました。')
                return
            doc = _app.activeDocument
            if not doc:
                _show_message('保存するドキュメントが開かれていません。')
                return
            if not doc.isSaved:
                _show_message(
                    'このドキュメントはまだ一度も保存されていません。\n\n'
                    '先にFusion標準の「名前を付けて保存」で保存先とファイル名を指定してください。'
                )
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
            if not description:
                _show_message('説明が空欄のため、保存を中止しました。')
                return
            doc = _app.activeDocument
            if not doc:
                _show_message('保存するドキュメントが見つかりません。')
                return
            if not doc.isSaved:
                _show_message(
                    'このドキュメントは未保存のため、説明付き保存を実行できません。\n'
                    '先に「名前を付けて保存」を実行してください。'
                )
                return
            result = doc.save(description)
            if result:
                _show_message('説明付きで保存しました。\n\nバージョンの説明：\n' + description)
            else:
                _show_message('Fusionが保存に失敗したと報告しました。ネットワーク接続やデータパネルを確認してください。')
        except:
            _show_message('説明付き保存中にエラーが発生しました。\n\n' + traceback.format_exc())

def run(context):
    global _app, _ui, _custom_save_event, _custom_save_handler
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

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

        qat = _ui.toolbars.itemById('QAT')
        if not qat:
            _show_message('ツールバーの取得に失敗しました。')
            return
            
        # 1. ファイルメニューをIDではなく「ドロップダウン」プロパティから動的に検索する
        file_menu = None
        for ctrl in qat.controls:
            if ctrl.objectType == adsk.core.DropDownControl.classType():
                # IDに 'file' または 'app' が含まれるドロップダウンをファイルメニューとみなす
                if 'file' in ctrl.id.lower() or 'app' in ctrl.id.lower():
                    file_menu = ctrl
                    break

        control = None
        if file_menu:
            control = file_menu.controls.itemById(COMMAND_ID)
            if not control:
                try:
                    # 標準の「名前を付けて保存 (SaveAsCommand)」の上に挿入
                    control = file_menu.controls.addCommand(cmd_def, 'SaveAsCommand')
                except:
                    # 失敗したらメニューの一番下に追加
                    control = file_menu.controls.addCommand(cmd_def)
        
        # 2. ファイルメニューが見つからなかった、または追加に失敗した場合のフォールバック
        if not control:
            control = qat.controls.itemById(COMMAND_ID)
            if not control:
                try:
                    # QAT（左上のツールバー）の標準保存ボタンの隣（Undoの前）に配置
                    control = qat.controls.addCommand(cmd_def, 'UndoCommand')
                except:
                    control = qat.controls.addCommand(cmd_def)

        if control:
            control.isVisible = True
        else:
            _show_message('ボタンの追加に失敗しました。')

    except:
        _show_message('アドインの起動中にエラーが発生しました。\n\n' + traceback.format_exc())


def stop(context):
    global _app, _ui, _custom_save_event, _custom_save_handler
    try:
        if _ui:
            qat = _ui.toolbars.itemById('QAT')
            if qat:
                # ファイルメニュー内のクリーンアップ
                for ctrl in qat.controls:
                    if ctrl.objectType == adsk.core.DropDownControl.classType() and ('file' in ctrl.id.lower() or 'app' in ctrl.id.lower()):
                        for c_id in (COMMAND_ID, 'FusionDescribedSaveCommandV7'):
                            control = ctrl.controls.itemById(c_id)
                            if control:
                                control.deleteMe()
                                
                # QAT直下のクリーンアップ（フォールバック時）
                for c_id in (COMMAND_ID, 'FusionDescribedSaveCommandV7'):
                    control = qat.controls.itemById(c_id)
                    if control:
                        control.deleteMe()

            for command_id in (COMMAND_ID, 'FusionDescribedSaveCommandV7'):
                cmd_def = _ui.commandDefinitions.itemById(command_id)
                if cmd_def:
                    cmd_def.deleteMe()

        if _app:
            for event_id in (CUSTOM_EVENT_ID, 'FusionDescribedSaveDeferredEventV7'):
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