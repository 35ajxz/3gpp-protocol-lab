/* Auto-generated bootstrap Promela for 5.3.13 RRC connection resume */
mtype = { RRC_CONNECTED, RRC_IDLE, RRC_INACTIVE, RRC_RESUME_REQUESTED };

active proctype procedure_model() {
  mtype state = RRC_INACTIVE;
  do
  :: (state == RRC_INACTIVE) -> /* upper_layers_resume_request | start_timer(T319); send_message(RRCResumeRequest,resumeIdentity) */ state = RRC_RESUME_REQUESTED;
  :: (state == RRC_RESUME_REQUESTED && (fullConfig_present)) -> /* receive(RRCResume) | stop_timer(T319); perform_full_configuration; release_suspendConfig_keep_rna */ state = RRC_CONNECTED;
  :: (state == RRC_RESUME_REQUESTED && (not fullConfig_present and masterCellGroup_present)) -> /* receive(RRCResume) | stop_timer(T319); apply_masterCellGroup_delta; update_radioBearerConfig_if_present; update_skCounter_if_present */ state = RRC_CONNECTED;
  :: (state == RRC_RESUME_REQUESTED) -> /* receive(RRCReject) | stop_timer(T319); clear_resume_context */ state = RRC_IDLE;
  :: (state == RRC_RESUME_REQUESTED) -> /* timer_expiry(T319) | clear_resume_context; reselect_cell */ state = RRC_IDLE;
  od
}
