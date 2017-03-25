How to use
==========

inside virtualenv
-----------------

    $ virtualenv ve
    $ source ve/bin/activate
    $ pip install -r requirements.txt
    $ python main.py

Press F1 to change IPV6 address of Node - or edit `osd_led_.ini`

on adroid
---------

install the apk, or build it by yourself ;)

To build, first install android ndk and sdk and python-for-android according to documentation in p4a/README.md

Then build the apk: 

    $ p4a apk --private single/ \
              --package=org.osdomotics.single_rgb_controller \
	      --name "OSDomotics Single RGB Controller" \
	      --version 1.0 \
	      --bootstrap=sdl2 \
	      --requirements=python2,sdl2,kivy,twisted,ipaddress \
	      --android_api=21 \
	      --ndk_dir=/opt/android-ndk/ \
	      --arch=armeabi-v7a \
	      --permission=INTERNET

have fun,
mexx.

