using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace TNG.Boxing.Editor {
public static class TngBuild {
 static string Prepare() {
  Directory.CreateDirectory("Assets/Generated");
  var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
  string path="Assets/Generated/Arena.unity";EditorSceneManager.SaveScene(scene,path);EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(path,true)};
  if(!AssetDatabase.LoadAssetAtPath<Material>("Assets/Resources/BoxerMaterial.mat"))AssetDatabase.CreateAsset(new Material(Shader.Find("Standard")),"Assets/Resources/BoxerMaterial.mat");
  PlayerSettings.companyName="TNG Boxing";PlayerSettings.productName="TNG Boxing Arena";PlayerSettings.bundleVersion="0.1.0";PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,"com.tngboxing.arena");
  AssetDatabase.SaveAssets();return path;
 }
 [MenuItem("TNG/Build Web game")]
 public static void Web(){
  string scene=Prepare();string root=Environment.GetEnvironmentVariable("TNG_UNITY_WEB_OUTPUT");if(string.IsNullOrWhiteSpace(root))root=Path.GetFullPath("../../frontend/public/boxing-unity");
  Directory.CreateDirectory(root);string manifest=Path.Combine(root,"manifest.json");if(File.Exists(manifest))File.Delete(manifest);
  PlayerSettings.WebGL.compressionFormat=WebGLCompressionFormat.Disabled;PlayerSettings.WebGL.template="PROJECT:TNG";PlayerSettings.WebGL.dataCaching=true;
  var r=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scene},locationPathName=root,target=BuildTarget.WebGL,options=BuildOptions.None});if(r.summary.result!=BuildResult.Succeeded)throw new Exception("Unity Web build failed: "+r.summary.result);
  File.WriteAllText(manifest,"{\"version\":\"0.1.0\",\"entry\":\"index.html\",\"engine\":\"Unity 6\"}");Debug.Log("TNG_WEB_BUILD_SUCCESS "+root);
 }
 [MenuItem("TNG/Build Android APK")]
 public static void Android(){string scene=Prepare();Directory.CreateDirectory("Builds");PlayerSettings.defaultInterfaceOrientation=UIOrientation.AutoRotation;PlayerSettings.Android.minSdkVersion=AndroidSdkVersions.AndroidApiLevel26;var r=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scene},locationPathName="Builds/TNG-Boxing.apk",target=BuildTarget.Android,options=BuildOptions.Development});if(r.summary.result!=BuildResult.Succeeded)throw new Exception("Android build failed");}
}
}
