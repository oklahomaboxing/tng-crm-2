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
  MuiTabs:{styleOverrides:{root:{minHeight:48,borderBottom:`1px solid ${line}`},indicator:{height:3,borderRadius:3}}},
  MuiTab:{styleOverrides:{root:{textTransform:'none',fontWeight:750,minHeight:48,minWidth:100}}},
  MuiAccordion:{styleOverrides:{root:{backgroundImage:'none',boxShadow:'none',border:`1px solid ${line}`,'&:before':{display:'none'}}}},
  MuiAccordionSummary:{styleOverrides:{root:{minHeight:56},content:{marginBlock:14}}},
  MuiMenu:{styleOverrides:{paper:{border:`1px solid ${line}`,borderRadius:14,boxShadow:'0 16px 48px #0b102b1c'}}},
  MuiMenuItem:{styleOverrides:{root:{minHeight:44,fontSize:14}}},
  MuiDialogTitle:{styleOverrides:{root:{fontWeight:800,padding:'24px 24px 16px'}}},
  MuiDialogActions:{styleOverrides:{root:{padding:'16px 24px',gap:8}}},
  MuiTablePagination:{styleOverrides:{toolbar:{minHeight:56},selectLabel:{fontSize:13},displayedRows:{fontSize:13}}},
  MuiSkeleton:{styleOverrides:{root:{backgroundColor:'#e3e8f0'}}},
 }
});
