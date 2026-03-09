/* Auto-generated bootstrap Promela for 5.3.3 RRC connection establishment */
mtype = { RRC_CONNECTED, RRC_IDLE, RRC_SETUP_REQUESTED };

active proctype procedure_model() {
  mtype state = RRC_IDLE;
  do
  :: (state == RRC_IDLE) -> /* upper_layers_request | start_timer(T300); send_message(RRCSetupRequest,ue_Identity,establishmentCause) */ state = RRC_SETUP_REQUESTED;
  :: (state == RRC_SETUP_REQUESTED && (fullConfig_present)) -> /* receive(RRCSetup) | stop_timer(T300); reset_as_context; deliver_dedicatedNAS_if_present */ state = RRC_CONNECTED;
  :: (state == RRC_SETUP_REQUESTED) -> /* timer_expiry(T300) | increment_setup_attempt; discard_pending_setup */ state = RRC_IDLE;
  od
}
