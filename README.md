## ccbuild

`ccbuild`将`python`开发的项目、流程或脚本文件进行编译成`C`的动态共享库`*.so`文件，不影响项目运行，可用于某些场景下`python`源码保护。



#### 依赖

+ Linux
+ Python >=2.7.10, <=3.10 and Python3 for recommend

+ cython



#### 安装

```
pip install git+https://github.com/yodeng/ccbuild.git
```



#### 使用

```
$ ccbuild -h 
```

相关参数解释如下：

| 参数                  | 描述                                                         |
| --------------------- | ------------------------------------------------------------ |
| -h/--help             | 打印帮助并退出                                               |
| -p/--python           | 编译后运行项目使用的python解释器路径，非绝对路径会从$PATH中查找 |
| -i/--input            | 需要编译的py文件或项目目录                                   |
| -o/--output           | 编译后的项目或文件输出路径                                   |
| -t/--threads          | cpu核数，默认5                                               |
| -c/--compile-continue | 若某个文件编译失败，是否跳过，继续编译，默认编译失败退出程序 |
| --exclude-dir         | 跳过的编译目录，默认"\_\_pycache\_\_"会被跳过, 多个输入空白隔开，支持简单shell匹配 |
| --exclude-file        | 跳过的编译文件，默认"\_\_init\_\_.py"会被跳过，多个输入空白隔开，支持简单shell匹配 |
| -v/--version          | 打印版本并退出                                               |



#### 说明

（1）编译后的输出目录，使用方式不变，只是项目中的`py`文件变成了`so`二进制文件。

（2）有可能存在编译失败的情况，原因是由于`python`代码中有`cython`识别不了的错误，`cython`和`python`并不是百分百兼容，需要调整`python`代码即可通过编译。