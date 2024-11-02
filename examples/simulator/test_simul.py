"""
An example of simulation using only basic rules
"""

# ---------------------------------------------------------------------------

import net_sim_builder

# --------------------------------------------------
# Rule as in documentation

frag_rule_noack = {
    "RuleID" : 12,
    "RuleIDLength" : 6,
    "Fragmentation" : {
        "FRMode": "NoAck",
        "FRDirection" : "DW"
    }
}

no_compression = {
    "RuleID" : 12,
    "RuleIDLength": 4,
    "NoCompression" : []
}

# ---------------------------------------------------------------------------

core_rules = [frag_rule_noack.copy(), no_compression.copy()]
device_rules = [frag_rule_noack.copy(), no_compression.copy()]

# --------------------------------------------------
# Message

coap_ip_packet = bytearray(b"""`\
\x12\x34\x56\x00\x1e\x11\x1e\xfe\x80\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x01\xfe\x80\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x02\x16\
2\x163\x00\x1e\x00\x00A\x02\x00\x01\n\xb3\
foo\x03bar\x06ABCD==Fk=eth0\xff\x84\x01\
\x82  &Ehello""")

# ---------------------------------------------------------------------------

builder = net_sim_builder.SimulBuilder()
#builder.set_config(net_sim_builder.DEFAULT_SIMUL_CONFIG, net_sim_builder.DEFAULT_LOSS_CONFIG)
builder.create_simul()
builder.create_device(device_rules)
builder.create_core(core_rules)

# ---------------------------------------------------------------------------
# Simnulation

builder.make_device_send_data(clock=1, packet=coap_ip_packet)
builder.run_simul()

# ---------------------------------------------------------------------------
