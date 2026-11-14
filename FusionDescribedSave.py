# Fusion Described Save v1.0.1
# Autodesk Fusion Python Add-In
# Uses Fusion's native modal inputBox for a classic one-line description popup.

import adsk.core
import adsk.fusion
import traceback

_app = None
_ui = None
_handlers = []
_custom_save_event = None
_custom_save_handler = None

ADDIN_NAME = 'FusionDescribedSave'
COMMAND_ID = 'FusionDescribedSaveCommandV6'
COMMAND_NAME = '説明付き保存'
COMMAND_DESCRIPTION = '説明を入力して、現在のデザインを説明付きで保存します。'
CUSTOM_EVENT_ID = 'FusionDescribedSaveDeferredEventV6'
QAT_ID = 'QAT'  # Quick Access Toolbar (upper-left area)


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
            # Native modal dialog, similar to Fusion's older description prompt.
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

        # Add a context-independent button to the upper-left Quick Access Toolbar.
        # QAT is available across Fusion workspaces, including Electronics workflows.
        qat = _ui.toolbars.itemById(QAT_ID)
        if not qat:
            _show_message('クイックアクセスツールバー（QAT）が見つかりませんでした。')
            return

        control = qat.controls.itemById(COMMAND_ID)
        if not control:
            control = qat.controls.addCommand(cmd_def)

        if control:
            control.isVisible = True
        else:
            _show_message('アドインは起動しましたが、QATへのボタン追加に失敗しました。')

    except:
        _show_message('アドインの起動中にエラーが発生しました。\n\n' + traceback.format_exc())


def stop(context):
    global _app, _ui, _custom_save_event, _custom_save_handler
    try:
        if _ui:
            # Remove the QAT button created by this add-in.
            qat = _ui.toolbars.itemById(QAT_ID)
            if qat:
                control = qat.controls.itemById(COMMAND_ID)
                if control:
                    control.deleteMe()

            # Also remove older versions that may have been placed in workspace panels.
            workspace = _ui.workspaces.itemById('FusionSolidEnvironment')
            if workspace:
                for panel_id in ('SolidCreatePanel', 'SolidModifyPanel'):
                    panel = workspace.toolbarPanels.itemById(panel_id)
                    if panel:
                        for control_id in (
                            COMMAND_ID,
                            'FusionDescribedSaveCommand',
                            'FusionDescribedSaveCommandV4',
                            'FusionDescribedSaveCommandV5',
                        ):
                            control = panel.controls.itemById(control_id)
                            if control:
                                control.deleteMe()

            for command_id in (
                'FusionDescribedSaveCommand',
                'FusionDescribedSaveCommandV4',
                'FusionDescribedSaveCommandV5',
            ):
                cmd_def = _ui.commandDefinitions.itemById(command_id)
                if cmd_def:
                    cmd_def.deleteMe()

        if _app:
            for event_id in (
                'FusionDescribedSaveDeferredEvent',
                'FusionDescribedSaveDeferredEventV4',
                'FusionDescribedSaveDeferredEventV5',
                CUSTOM_EVENT_ID,
            ):
                try:
                    _app.unregisterCustomEvent(event_id)
                except:
                    pass

    except:
        _show_message('アドイン停止時にエラーが発生しました。\n\n' + traceback.format_exc())
    finally:
        _handlers.clear()
        _custom_save_event = None
        _custom_save_handler = None
        _app = None
        _ui = None
