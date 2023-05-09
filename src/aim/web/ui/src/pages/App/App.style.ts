import { styled } from 'config/stitches';
import { LayoutContainer } from 'config/stitches/foundations/layout';

import { Box } from '../../components/kit_v2';

const AppContainer = styled(LayoutContainer, {
  $$space: '$space$15',
  py: '$$space',
  overflowY: 'auto',
});

const BoardContainer = styled(Box, {
  mt: '$6',
});

const BoardWrapper = styled(Box, {
  border: '1px solid #B5C4D3',
  p: '$4',
  mt: '$4',
});

export { AppContainer, BoardContainer, BoardWrapper };
