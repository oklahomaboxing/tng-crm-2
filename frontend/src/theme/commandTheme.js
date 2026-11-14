import {createTheme} from '@mui/material';
import standard from './tngTheme';
export default createTheme(standard,{
 palette:{mode:'dark',primary:{main:'#66dfff',dark:'#1a9bbe',contrastText:'#03131e'},secondary:{main:'#a6b6ff'},text:{primary:'#e6f4ff',secondary:'#abc4d8'},background:{default:'#06111e',paper:'#0b2033'},divider:'#295168',error:{main:'#ff6b80'},warning:{main:'#ffd180'},success:{main:'#63e3bc'}},
 components:{
  MuiCard:{styleOverrides:{root:{background:'linear-gradient(145deg,rgba(17,44,64,.92),rgba(6,23,39,.88))',border:'1px solid #75dfff35',boxShadow:'0 14px 44px #0005, inset 0 1px 0 #c4efff18',backdropFilter:'blur(16px)',color:'#e6f4ff'}}},
  MuiButton:{styleOverrides:{containedPrimary:{background:'linear-gradient(120deg,#66dfff,#38a9d5)',color:'#03131e',boxShadow:'0 0 20px #42caff24'},outlined:{borderColor:'#62cbea66'}}},
  MuiOutlinedInput:{styleOverrides:{root:{backgroundColor:'#04111e70','& fieldset':{borderColor:'#3b6d87'},'&:hover fieldset':{borderColor:'#79d9fa'}}}},
  MuiTableHead:{styleOverrides:{root:{backgroundColor:'#112d42','& .MuiTableCell-root':{color:'#bfeeff'}}}},
  MuiTableCell:{styleOverrides:{root:{borderBottom:'1px solid #2a4b60'}}},
  MuiTableRow:{styleOverrides:{root:{'&.MuiTableRow-hover:hover':{backgroundColor:'#16344a'}}}},
  MuiDialog:{styleOverrides:{paper:{backgroundColor:'#0c2032',border:'1px solid #62cbea55',color:'#e6f4ff'}}},
  MuiSkeleton:{styleOverrides:{root:{backgroundColor:'#25465b'}}},
  MuiAccordion:{styleOverrides:{root:{backgroundColor:'#0c2032',color:'#e6f4ff'}}},
 }
});
