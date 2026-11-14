# Fusion Described Save v1.0.2
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
COMMAND_ID = 'FusionDescribedSaveCommandV7' # 古いボタンと干渉しないようIDを更新
COMMAND_NAME = '説明付き保存'
COMMAND_DESCRIPTION = '説明を入力して、現在のデザインを説明付きで保存します。'
CUSTOM_EVENT_ID = 'FusionDescribedSaveDeferredEventV7'

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

        # ファイルメニュー（アプリケーションメニュー）を取得
        qat = _ui.toolbars.itemById('QAT')
        if not qat:
            _show_message('ツールバーの取得に失敗しました。')
            return
            
        file_menu = qat.controls.itemById('FileSubMenu')
        if not file_menu:
            _show_message('ファイルメニューが見つかりませんでした。')
            return

        control = file_menu.controls.itemById(COMMAND_ID)
        if not control:
            # 標準の「名前を付けて保存 (SaveAsCommand)」の上に挿入を試みる
            # 成功すれば標準の「保存」と「名前を付けて保存/バージョンを作成」の間に配置されます
            try:
                control = file_menu.controls.addCommand(cmd_def, 'SaveAsCommand')
            except:
                # 失敗した場合はメニューの最後に追加
                control = file_menu.controls.addCommand(cmd_def)

        if control:
            control.isVisible = True
        else:
            _show_message('アドインは起動しましたが、ファイルメニューへのボタン追加に失敗しました。')

    except:
        _show_message('アドインの起動中にエラーが発生しました。\n\n' + traceback.format_exc())


def stop(context):
    global _app, _ui, _custom_save_event, _custom_save_handler
    try:
        if _ui:
            # FileSubMenuからのクリーンアップ
            qat = _ui.toolbars.itemById('QAT')
            if qat:
                file_menu = qat.controls.itemById('FileSubMenu')
                if file_menu:
                    for c_id in (COMMAND_ID, 'FusionDescribedSaveCommandV6'):
                        control = file_menu.controls.itemById(c_id)
                        if control:
                            control.deleteMe()
                            
                # 以前のバージョン（QAT直下）のゴミが残っていれば消去
                for c_id in (COMMAND_ID, 'FusionDescribedSaveCommandV6'):
                    control = qat.controls.itemById(c_id)
                    if control:
                        control.deleteMe()

            for command_id in (COMMAND_ID, 'FusionDescribedSaveCommandV6'):
                cmd_def = _ui.commandDefinitions.itemById(command_id)
                if cmd_def:
                    cmd_def.deleteMe()

        if _app:
            for event_id in (CUSTOM_EVENT_ID, 'FusionDescribedSaveDeferredEventV6'):
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