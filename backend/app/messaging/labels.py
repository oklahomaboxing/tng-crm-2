"""Display labels for new outgoing work texts and inbox replies."""
def message_label(folder):
    return {'clubs':'LBC 27 Boxing Clubs','officials':'LBC 27 Boxing Officials'}.get(folder,'TNG Boxing')
