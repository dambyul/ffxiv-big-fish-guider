CHECK_SETUP = {
    "log_no_config": "⚠️ 서버 {guild_id} 에 초기화된 채널 없음 (/setup 필요)",
    "log_guild_config_cleanup_failed": "[{guild_id}] DB 설정 삭제 실패: {error}",
    "log_guild_missing": "[{guild_id}] 길드를 찾을 수 없음",
    "log_no_config": "[{guild_id}] 길드 설정이 없음",
    "log_channel_missing": "[{channel_id}] 채널이 존재하지 않음",
    "log_channel_forbidden": "[{channel_id}] 채널 접근 권한 없음",
    "log_channel_fetch_failed": "[{channel_id}] 채널 불러오기 실패: {error}",
    "log_old_message_forbidden": "[{channel_id}/{message_id}] 기존 메시지 접근 권한 없음",
    "log_old_message_fetch_failed": "[{channel_id}/{message_id}] 기존 메시지 불러오기 실패: {error}",
    "log_old_message_edit_forbidden": "[{channel_id}/{message_id}] 기존 메시지 수정 권한 없음",
    "log_old_message_edit_failed": "[{channel_id}/{message_id}] 기존 메시지 수정 실패: {error}",
    "log_old_message_delete_failed": "기존 메시지 삭제 실패: {error}",
    "log_guide_message_updated": "[{channel_id}/{message_id}] 안내 메시지 갱신 완료",
    "log_guide_message_sent": "[{channel_id}/{message_id}] 안내 메시지 새로 작성 완료",
    "log_guide_message_send_forbidden": "[{channel_id}] 안내 메시지 전송 권한 없음",
    "log_guide_message_send_failed": "안내 메시지 전송 실패: {error}"
}

DM_UPLOAD = {
    "error_user": "❌ {error}",
    "error_unknown": "❌ 알 수 없는 오류: {error}",
}

THREAD_UPLOAD = {
    "error_user": "❌ {error}",
    "error_unknown": "❌ 처리 중 오류 발생: {error}",
    "success_and_delete": "✅ 처리 완료! 스레드는 자동으로 삭제됩니다.",
    "need_json": "❌ JSON 형식 텍스트나 .json/.txt 파일을 보내주세요.",
}

SETUP_COMMAND = {
    "name": "setup",
    "description": "안내 채널 및 메시지를 생성합니다.",
    "arg_channel_name": "생성할 채널 이름 (예: 터쭈)",
    "error_not_in_guild": "❌ 서버에서만 사용할 수 있습니다.",
    "success_channel_created": "✅ 채널 및 안내 메시지를 설정했습니다: {channel_mention}",
    "guide_message": (
        "🎣 https://ff14fish.carbuncleplushy.com/ 에서 Export Settings를 눌러 추출한 JSON을 DM으로 전송하면 자동 저장됩니다.\n"
        "DM외에도 /update 명령어로 전용 스레드를 만들어 해당 스레드에 전송도 가능합니다.\n"
        "/fish 명령어로 물고기 정보를 검색할 수 있습니다. (한글, 영어, 일본어 명칭 지원)"
    ),
    "log_fetch_old_channel_failed": "[SETUP] 이전 채널 조회 실패: {error}",
    "log_old_message_delete_failed": "[SETUP] 이전 안내 메시지 삭제 실패: {error}",
    "log_guide_message_send_failed": "[SETUP] 안내 메시지 전송 실패: {error}",
    "log_channel_permission_fix_failed": "[SETUP] 채널 권한 보정 실패: {error}",
    "error_missing_perms": "❌ 권한 부족으로 안내 메시지를 보낼 수 없습니다.",
}

UPDATE_COMMAND = {
    "name": "update",
    "description": "데이터 업로드 전용 스레드를 생성합니다.",

    # 사용자 안내 메시지
    "error_guild_only": "❌ 이 명령은 서버에서만 사용할 수 있습니다.",
    "error_setup_required": "서버에 전용 채널이 설정되지 않았습니다. 먼저 /setup 으로 전용 채널을 생성하세요. (관리자 권한 필요)",
    "error_cannot_access_channel": "전용 채널에 접근 권한이 없습니다. 권한을 부여하거나 /setup 을 다시 진행해 주세요.",
    "error_wrong_setup_channel_type": "전용 채널이 텍스트 채널이 아닙니다. /setup 을 다시 진행해 주세요.",
    "error_missing_perms": "권한 부족으로 스레드를 만들 수 없습니다. (View Channel, Send Messages, Create Public Threads, Send Messages in Threads 필요)",
    "error_unknown": "알 수 없는 오류가 발생했습니다. 로그를 확인해 주세요.",

    # 스레드 안내/성공 메시지
    "thread_message_prompt": "{mention}, JSON 텍스트를 보내거나 .json/.txt 파일을 업로드해 주세요.",
    "success_thread_created": "🧵 전용 스레드를 생성했습니다. 위치: {channel_mention}",

    # 로그 메시지
    "log_fetch_channel_failed": "[ERROR] 설정 채널 조회 실패: {error}",
    "log_old_thread_delete_failed": "[WARN] 이전 스레드 삭제 실패: {error}",
    "log_create_thread_failed": "[ERROR] 스레드 생성 실패: {error}",
}

FISH_COMMAND = {
    "name": "fish",
    "description": "물고기 이름으로 낚시 정보를 조회합니다.",
    "arg_name": "물고기 이름 또는 ID",
    "not_found": "❌ 해당 이름의 물고기를 찾을 수 없습니다."
}

JSON_PARSE = {
    "missing_completed": "❌ JSON 객체에 'completed' 필드가 없습니다.",
    "invalid_format": "❌ JSON은 배열이거나 'completed' 필드를 포함한 객체여야 합니다.",
    "non_integer": "❌ 물고기 ID 배열에 숫자 외 값이 포함되어 있습니다.",
    "first_save": "🎉 처음으로 물고기 정보를 저장했습니다!",
    "no_new_fish": "🐟 새롭게 잡은 물고기가 없습니다.",
    "new_fish_header": "🎣 새로 잡은 물고기 목록입니다:\n",
}

MAIN_BTN = {
    "merge_button_label": "리스트 만들기",
    "merge_prompt": "📋 유저 선택하기",
    "thread_button_label": "스레드 만들기",
    "thread_prompt": "📋 유저 선택하기",
    "not_invoker": "❌ 이 버튼은 {mention}만 사용할 수 있습니다.",
}

USER_SELECT = {
    "prompt": "📋 유저 선택하기",
    "placeholder": "📋 유저 선택하기",
    "timeout_sec": 60,
    "min_values": 2,
    "max_values": 10,
}

USER_SELECT_MERGE = {
    "no_config": "❌ 선택한 사람 중 설정이 업로드된 사람이 없어요.",
    "reply_done": (
        "✅ 작업이 완료되었습니다.\n"
        "아래 결과 데이터를 Fish Tracker App에 Import 해주세요.\n"
        "기존 설정을 업로드 해두지 않으면 본인의 세팅이 사라지니 백업해두세요."
    ),
    "reply_missing_users": "❗ 설정이 업로드되지 않은 사람이 포함되어 있습니다: {users}",
    "tempfile_suffix": ".json",
    "tempfile_filename": "merged_fish.json",
}

USER_SELECT_THREAD = {
    "duplicate_found": "🧵 이미 생성된 스레드가 있습니다: {url}",
    "created_notice_ephemeral": "🧵 새 스레드를 생성했습니다.",
    "thread_head": "🧵 {mention}님이 생성한 스레드입니다.\n참여 유저: {mentions}",
    "name_sep": " / ",
    "auto_archive_min": 60,
    "created_reason": "Created by {user}",
}