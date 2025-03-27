import { ViroARScene, Viro3DObject } from '@viro-community/react';

export default function ARViewer({ modelUrl, scale = [1, 1, 1] }) {
  return (
    <ViroARScene onTrackingUpdated={console.log}>
      <Viro3DObject 
        source={{ uri: modelUrl }}
        scale={scale}
        type="OBJ"
        position={[0, 0, -2]}
        rotation={[-90, 0, 0]}
      />
    </ViroARScene>
  );
}