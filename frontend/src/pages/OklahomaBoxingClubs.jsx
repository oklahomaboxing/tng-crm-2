import React from 'react';
import {Stack,Typography} from '@mui/material';
import AmateurDirectory from './AmateurDirectory';
export default function OklahomaBoxingClubs(){
 return <Stack spacing={2}><Typography variant="overline" color="primary">TNG BOXING / CLUB CONTACTS</Typography><AmateurDirectory kind="club" stateFilter="OK"/></Stack>;
}
