/* Auto-generated bootstrap Promela for 5.3.5.11 Full configuration procedure */
mtype = { RRC_CONFIGURATION_APPLIED, RRC_CONFIGURATION_PENDING };

active proctype procedure_model() {
  mtype state = RRC_CONFIGURATION_PENDING;
  do
  :: (state == RRC_CONFIGURATION_PENDING) -> /* fullConfig_present | reset_mac; reset_rlc; reconfigure_srb1 */ state = RRC_CONFIGURATION_APPLIED;
  od
}
