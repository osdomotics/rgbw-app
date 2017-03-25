Enable IPV6 support in python-for-android
=========================================

Install python-for-android
--------------------------

    $ sudo pip install python-for-android

for datails take a look at see https://python-for-android.readthedocs.io/en/latest/ 


Modify to add support for IPV6
------------------------------

copy `patches/ipv6.patch` to python-for-android install, e.g.: 

    $ sudo cp patches/ipv6.patch /usr/lib/python2.7/site-packages/pythonforandroid/recipes/python2/patches/ipv6.patch

edit `recipes/python2/__init__.py` e.g.:

    $ sudo vi /usr/lib/python2.7/site-packages/pythonforandroid/recipes/python2/__init__.py

add `patches/ipv6.patch` at the beginning of the `patches` array at the top

add `--enable-ipv6` to the configure arguments (around line 120)

