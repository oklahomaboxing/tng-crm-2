import {createTheme} from '@mui/material';
const ink='#111827',muted='#647084',line='#e1e6ee';
export default createTheme({
 palette:{mode:'light',primary:{main:'#d71932',dark:'#ac1026'},error:{main:'#cf233a'},secondary:{main:'#087f9b'},text:{primary:ink,secondary:muted},background:{default:'#eef1f6',paper:'#ffffff'},divider:line,success:{main:'#087b63'},warning:{main:'#a65d09'}},
 shape:{borderRadius:16},
 typography:{fontFamily:'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',h3:{fontWeight:850,letterSpacing:'-.055em'},h4:{fontWeight:850,letterSpacing:'-.04em'},h5:{fontWeight:800,letterSpacing:'-.025em'},h6:{fontWeight:800,letterSpacing:'-.02em'},button:{textTransform:'none',fontWeight:750},overline:{fontWeight:800,letterSpacing:2,fontSize:10}},
 components:{
  MuiCssBaseline:{styleOverrides:{body:{fontVariantNumeric:'tabular-nums'},'::selection':{background:'#d7193226'},':focus-visible':{outline:'3px solid #20a9c3',outlineOffset:3},'@media (prefers-reduced-motion: reduce)':{'*, *::before, *::after':{animation:'none !important',transition:'none !important',scrollBehavior:'auto !important'}}}},
  MuiButton:{defaultProps:{disableElevation:true},styleOverrides:{root:{borderRadius:11,minHeight:44,paddingInline:18},outlined:{borderColor:'#cdd5e1'},containedPrimary:{background:'linear-gradient(110deg,#d71932,#b7132a)',boxShadow:'0 4px 12px #d719321c'}}},
  MuiIconButton:{styleOverrides:{root:{minWidth:44,minHeight:44,borderRadius:11}}},
  MuiCard:{styleOverrides:{root:{border:`1px solid ${line}`,boxShadow:'0 4px 20px rgba(15,23,42,.035)',backgroundImage:'none'}}},
  MuiCardContent:{styleOverrides:{root:{padding:24,'&:last-child':{paddingBottom:24},'@media(max-width:600px)':{padding:18,'&:last-child':{paddingBottom:18}}}}},
  MuiOutlinedInput:{styleOverrides:{root:{borderRadius:11,backgroundColor:'#ffffff70','& fieldset':{borderColor:'#d5dce6'},'&:hover fieldset':{borderColor:'#94a3b8'}}}},
  MuiTextField:{defaultProps:{size:'small'}},
  MuiChip:{styleOverrides:{root:{fontWeight:700,borderRadius:8}}},
  MuiTableHead:{styleOverrides:{root:{backgroundColor:'#f3f6fa','& .MuiTableCell-root':{fontSize:11,fontWeight:800,textTransform:'uppercase',letterSpacing:'.06em',color:'#526075'}}}},
  MuiTableCell:{styleOverrides:{root:{borderBottom:`1px solid ${line}`,padding:'15px 18px'}}},
  MuiTableRow:{styleOverrides:{root:{'&.MuiTableRow-hover:hover':{backgroundColor:'#f7f9fc'}}}},
  MuiDialog:{styleOverrides:{paper:{borderRadius:20,border:`1px solid ${line}`,boxShadow:'0 28px 100px #0b102b33'}}},
  MuiAlert:{styleOverrides:{root:{borderRadius:12}}},
  MuiSkeleton:{styleOverrides:{root:{backgroundColor:'#e3e8f0'}}},
 }
});
