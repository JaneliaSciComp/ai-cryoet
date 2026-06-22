import { AppBar, Box, Toolbar, Typography, css, styled } from '@mui/material'
import { CustomLink } from './CustomLink'

const StyledCustomLink = styled(CustomLink)(
  ({ theme }) => css`
    color: ${theme.palette.common.white};
    font-weight: 500;
  `,
)

// The app name doubles as a "home" link, so style it like a heading but keep
// it a link for affordance + keyboard access.
const BrandLink = styled(CustomLink)(
  ({ theme }) => css`
    color: ${theme.palette.common.white};
    text-decoration: none;
    font-weight: 700;
  `,
)

export function Header() {
  return (
    <Box>
      <AppBar position="static">
        <Toolbar sx={{ gap: 3 }}>
          <BrandLink to="/">
            <Typography variant="h6" component="span">
              AI+CryoET Data Portal
            </Typography>
          </BrandLink>
          <Box sx={{ flexGrow: 1 }} />
          <StyledCustomLink to="/experimental">
            Experimental Data
          </StyledCustomLink>
          <StyledCustomLink to="/md-simulation">
            MD Simulations
          </StyledCustomLink>
          <StyledCustomLink to="/manage">Manage</StyledCustomLink>
        </Toolbar>
      </AppBar>
    </Box>
  )
}
