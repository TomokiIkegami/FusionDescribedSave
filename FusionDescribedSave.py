# Fusion Described Save v1.0.7
# Autodesk Fusion Python Add-In

import adsk.core
import adsk.fusion
import traceback

_app = None
_ui = None
_handlers = []

# 保存実行用イベント
CUSTOM_SAVE_EVENT_ID = 'FusionDescribedSaveEvent_V12'
_custom_save_event = None
_custom_save_handler = None

# UI再構築（遅延実行）用イベント
CUSTOM_REBUILD_EVENT_ID = 'FusionDescribedSaveRebuild_V12'
_custom_rebuild_event = None
_custom_rebuild_handler = None

ADDIN_NAME = 'FusionDescribedSave'
COMMAND_ID = 'FusionDescribedSaveCmd_V12'
COMMAND_NAME = '説明付き保存'
COMMAND_DESCRIPTION = '説明を入力して、現在のデザインを説明付きで保存します。'

def _show_message(message):
    try:
        if _ui: _ui.messageBox(message, ADDIN_NAME)
    except:
        pass

def force_rebuild_ui():
    """古いボタンを破壊し、新しいボタンを配置する実処理"""
    global _handlers
    try:
        if not _ui: return
        qat = _ui.toolbars.itemById('QAT')
        file_menu = None
        if qat:
            for ctrl in qat.controls:
                if ctrl.objectType == adsk.core.DropDownControl.classType() and ('file' in ctrl.id.lower() or 'app' in ctrl.id.lower()):
                    file_menu = ctrl
                    break

        # 1. クリーンアップ
        if file_menu:
            old_ctrl = file_menu.controls.itemById(COMMAND_ID)
            if old_ctrl: old_ctrl.deleteMe()
        if qat:
            old_qat = qat.controls.itemById(COMMAND_ID)
            if old_qat: old_qat.deleteMe()

        cmd_def = _ui.commandDefinitions.itemById(COMMAND_ID)
        if cmd_def: cmd_def.deleteMe()

        _handlers = [h for h in _handlers if not isinstance(h, SaveCommandCreatedHandler)]

        # 2. 再構築
        cmd_def = _ui.commandDefinitions.addButtonDefinition(COMMAND_ID, COMMAND_NAME, COMMAND_DESCRIPTION)
        
        on_created = SaveCommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        # 3. 再配置
        if file_menu:
            try:
                new_ctrl = file_menu.controls.addCommand(cmd_def, 'ExportCommand')
            except:
                try:
                    new_ctrl = file_menu.controls.addCommand(cmd_def, 'SaveAsCommand')
                except:
                    new_ctrl = file_menu.controls.addCommand(cmd_def)
            if new_ctrl: new_ctrl.isVisible = True
        elif qat:
            new_ctrl = qat.controls.addCommand(cmd_def)
            if new_ctrl: new_ctrl.isVisible = True
    except:
        pass


# ==========================================
# 遅延実行（イベントキューイング）用ハンドラ
# ==========================================
class RebuildUIEventHandler(adsk.core.CustomEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        # Fusion本体の重い処理が終わったあとに呼ばれる
        force_rebuild_ui()


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
            _app.fireCustomEvent(CUSTOM_SAVE_EVENT_ID, description)
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
# ワークスペース・ドキュメント切り替え検知
# ==========================================
class WorkspaceActivatedHandler(adsk.core.WorkspaceEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        # すぐにUIを作らず、Fusionの処理待ちキューに「あとで作ってね」と投げる
        if _app: _app.fireCustomEvent(CUSTOM_REBUILD_EVENT_ID)

class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        if _app: _app.fireCustomEvent(CUSTOM_REBUILD_EVENT_ID)


def run(context):
    global _app, _ui, _custom_save_event, _custom_save_handler, _custom_rebuild_event, _custom_rebuild_handler
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        
        adsk.autoTerminate(False)

        # 保存用カスタムイベント登録
        _custom_save_event = _app.registerCustomEvent(CUSTOM_SAVE_EVENT_ID)
        _custom_save_handler = DeferredSaveEventHandler()
        _custom_save_event.add(_custom_save_handler)
        _handlers.append(_custom_save_handler)

        # UI再構築用カスタムイベント登録（NEW!）
        _custom_rebuild_event = _app.registerCustomEvent(CUSTOM_REBUILD_EVENT_ID)
        _custom_rebuild_handler = RebuildUIEventHandler()
        _custom_rebuild_event.add(_custom_rebuild_handler)
        _handlers.append(_custom_rebuild_handler)

        # 切り替え検知リスナー登録
        on_workspace_activated = WorkspaceActivatedHandler()
        _ui.workspaceActivated.add(on_workspace_activated)
        _handlers.append(on_workspace_activated)

        on_document_activated = DocumentActivatedHandler()
        _app.documentActivated.add(on_document_activated)
        _handlers.append(on_document_activated)

        # 初回起動時のUI構築もキューに入れる
        _app.fireCustomEvent(CUSTOM_REBUILD_EVENT_ID)

    except:
        _show_message('起動中にエラーが発生しました。\n\n' + traceback.format_exc())


def stop(context):
    global _app, _ui, _custom_save_event, _custom_save_handler, _custom_rebuild_event, _custom_rebuild_handler
    try:
        if _ui:
            # --------------------------------------------------------
            # 1. 現在のバージョン（ファイルメニュー・QAT）のクリーンアップ
            # --------------------------------------------------------
            qat = _ui.toolbars.itemById('QAT')
            if qat:
                for ctrl in qat.controls:
                    if ctrl.objectType == adsk.core.DropDownControl.classType() and ('file' in ctrl.id.lower() or 'app' in ctrl.id.lower()):
                        # 今回の最新版のIDを削除
                        control = ctrl.controls.itemById(COMMAND_ID)
                        if control: control.deleteMe()
                            
                # QAT直下にある場合の削除
                control = qat.controls.itemById(COMMAND_ID)
                if control: control.deleteMe()

            # --------------------------------------------------------
            # 2. v1.0.0 以前（過去のリリース版）のゾンビUIのお掃除
            # --------------------------------------------------------
            workspace = _ui.workspaces.itemById('FusionSolidEnvironment')
            if workspace:
                # v1.0.0 で配置していたパネルを巡回
                for panel_id in ('SolidCreatePanel', 'SolidModifyPanel'):
                    panel = workspace.toolbarPanels.itemById(panel_id)
                    if panel:
                        # v1.0.0およびそれ以前のIDをすべて消去
                        for old_ctrl_id in (
                            'FusionDescribedSaveCommandV6',
                            'FusionDescribedSaveCommandV5',
                            'FusionDescribedSaveCommandV4',
                            'FusionDescribedSaveCommand'
                        ):
                            old_ctrl = panel.controls.itemById(old_ctrl_id)
                            if old_ctrl:
                                old_ctrl.deleteMe()

            # --------------------------------------------------------
            # 3. コマンド定義（コマンドそのもの）のお掃除
            # --------------------------------------------------------
            for cmd_id in (
                COMMAND_ID,
                'FusionDescribedSaveCommandV6',
                'FusionDescribedSaveCommandV5',
                'FusionDescribedSaveCommandV4',
                'FusionDescribedSaveCommand'
            ):
                cmd_def = _ui.commandDefinitions.itemById(cmd_id)
                if cmd_def: cmd_def.deleteMe()

        if _app:
            # --------------------------------------------------------
            # 4. バックグラウンドイベントのお掃除
            # --------------------------------------------------------
            for event_id in (
                CUSTOM_SAVE_EVENT_ID,
                CUSTOM_REBUILD_EVENT_ID,
                'FusionDescribedSaveDeferredEventV6',
                'FusionDescribedSaveDeferredEventV5',
                'FusionDescribedSaveDeferredEventV4',
                'FusionDescribedSaveDeferredEvent'
            ):
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
        _custom_rebuild_event = None
        _custom_rebuild_handler = None
        _app = None
        _ui = None